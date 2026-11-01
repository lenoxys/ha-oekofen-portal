"""Solar boost: raise the comfort setpoint on sunny days to heat the house with the buffer's surplus.

The comfort is raised as far as the buffer can supply without calling the boiler (adaptive target), from
the controller's own heating curve, and lowered at once when the buffer setpoint it then asks for gets
too close to the buffer top. Not when someone is home; only the surplus when everyone is far away.

ÖkoFEN's own solar discharge cannot do it (it starts at 82 °C, knows neither the hot water reserve
nor the sunset, and does not open the radiator heads). This module only decides; ``boost.py`` writes.
Does not import Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
import math

# short name -> portal variable
KEYS = {
    "top": "LOCAL.L_pu[0].einschaltfuehler_ist",
    "tank_set": "LOCAL.L_pu[0].einschaltfuehler_soll",  # above this the boiler is not asked
    "ecs": "LOCAL.L_ww[0].einschaltfuehler_ist",
    "ecs_set": "LOCAL.L_ww[0].temp_soll",
    "room": "LOCAL.L_hk[0].raumtemp_ist",
    "comfort": "LOCAL.hk[0].raumtemp_heizen",
    "mode": "LOCAL.hk[0].betriebsart[1]",  # 0 off
    "season": "LOCAL.anlage_betriebsart",  # 1 auto (heating + hot water)
    "outdoor": "LOCAL.L_aussentemperatur_ist",
    "heating_limit": "LOCAL.hk[0].heizgrenze_heizen",
    "flow_max": "LOCAL.hk[0].vorlauftemp_max",
    "overshoot": "LOCAL.hk[0].ueberhoehung",
    "forecast_clouds": "LOCAL.L_weather_forecast_clouds",
    "cloud_limit": "LOCAL.weather_limit",  # the controller's own "sunny" limit, %
    "burner": "LOCAL.L_ke_brennerkontakt_1",
    "sun": "LOCAL.L_weather[0]",  # "...|07:45|17:53": sunrise and sunset
    "room_set": "LOCAL.L_hk[0].raumtemp_soll",  # comfort + the controller's offsets (remote, eco)
    "curve_foot": "LOCAL.hk[0].heizkurve_fusspunkt",
    "curve_slope": "LOCAL.hk[0].heizkurve_steigung",
    # status bits: the buffer (0x100) or the hot water (0x4000) asks the boiler, a step before the burner starts
    "buffer_state": "LOCAL.L_pu[0].status",
    "ecs_state": "LOCAL.L_ww[0].status",
}
OPTIONAL = {"burner", "buffer_state", "ecs_state"}  # the burner (portal only) or the demand (also local) is enough
COMFORT_KEY = KEYS["comfort"]
DWELL = 600  # s between two changes, except to stop for the burner, a manual change or missing data
HYSTERESIS = 1.5  # K between the start and stop thresholds
# stops not delayed by DWELL (starts always wait): the buffer and hot water ones protect from the boiler
URGENT = {"burner", "manual", "missing_data", "heating_off", "occupied", "tank_cold", "hot_water_low"}
REASONS = (
    "running", "disabled", "missing_data", "burner", "manual", "occupied", "far_away", "heating_off", "outside_window",
    "cloudy", "mild_outdoor", "tank_cold", "hot_water_low", "room_warm", "dwell",
)
STEP = 0.5  # K: the comfort climbs by this much
STEP_DWELL = 120  # s between two steps up, so the controller's new buffer setpoint is read before the next one
# K the controller adds to its heating curve to catch up the room (seen up to +6 K on 30 Oct 2026, one house)
# ponytail: one margin for every house; learn it from flow_set against the curve if it turns out too tight or loose
ROOM_INFLUENCE = 8
HOME = ("armed_home", "armed_night")  # alarm states: someone is home
AWAY = ("armed_away", "armed_vacation")


@dataclass
class Options:
    target: float = 24  # highest comfort setpoint written while boosting, °C
    tank_threshold: float | None = None  # buffer top needed at least to start; None: only the heating curve decides
    hot_water_reserve: float = 55  # hot water probe kept above this, °C
    after_sunrise: int = 120  # minutes
    before_sunset: int = 90
    far_km: float = 30  # everyone further than this: no boost, except the surplus
    surplus: float = 80  # buffer top that is dumped into the house even when everyone is far away, °C

    @classmethod
    def from_dict(cls, d) -> Options:
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names and v is not None})


def sun_window(sun: str, after_sunrise: int, before_sunset: int) -> tuple[int, int] | None:
    """(start, end) in minutes of the day, from the first forecast string; None if unreadable."""
    parts = str(sun).split("|")
    try:
        (rh, rm), (sh, sm) = (map(int, p.split(":")) for p in parts[7:9])
    except (ValueError, IndexError):
        return None
    return rh * 60 + rm + after_sunrise, sh * 60 + sm - before_sunset


def need(comfort: float, v: dict) -> float:
    """Buffer top the controller asks for when the comfort is ``comfort``: its curve, the room catch-up, capped."""
    offset = v["room_set"] - v["comfort"] if v["room_set"] > 8 else 0  # 8 °C: the idle setpoint
    flow = v["curve_foot"] + v["curve_slope"] * (comfort + offset - v["outdoor"]) + ROOM_INFLUENCE
    return min(flow, v["flow_max"]) + v["overshoot"] + 1


def best(written: float | None, base: float, v: dict, opt: Options) -> float | None:
    """Highest comfort the buffer can supply, in steps above ``base``; None when not even one step."""
    margin = 0 if written is not None else HYSTERESIS
    top = v["top"]
    steps = int((opt.target - base) / STEP + 1e-9)
    found = None
    for k in range(1, steps + 1):
        if need(base + k * STEP, v) + margin > top:
            break
        found = base + k * STEP
    if written is not None and v["tank_set"] > 8 and v["tank_set"] + 1 > v["top"]:
        found = written - STEP if written - STEP > base else None  # the controller already asks more than the buffer holds
    return found


def presence(alarm: str | None, persons: list[tuple[str, float | None, float | None]], home: tuple[float, float] | None,
             far_km: float) -> str | None:
    """"home", "near", "far", or None when nothing says. ``persons``: (state, latitude, longitude) of each person.

    The alarm armed for the night means home, armed away means nobody home whatever the phones say;
    otherwise someone home is home, and the nearest person decides near or far.
    """
    if alarm in HOME:
        return "home"
    armed_away = away = alarm in AWAY
    distances = []
    for state, lat, lon in persons:
        if state in ("unknown", "unavailable", None):
            continue
        if state == "home" and not armed_away:
            return "home"
        away = True
        if lat is not None and lon is not None and home is not None:
            distances.append(_km(lat, lon, *home))
    if distances:
        return "near" if min(distances) <= far_km else "far"
    return "near" if away else None


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    return 6371 * 2 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def checks(written: float | None, now: datetime, v: dict, opt: Options, base: float | None = None) -> list[dict]:
    """Every condition, in order: ``id`` is the reason when it fails; ``value`` and ``limit`` are for the panel.

    ``written``: the comfort we set, None when not boosting (start thresholds, otherwise stop thresholds);
    ``base``: the comfort to put back (default the current one).
    """
    active = written is not None
    missing = any(v.get(k) is None for k in KEYS if k not in OPTIONAL) or v.get("burner") is None and v.get("buffer_state") is None
    window = None if missing else sun_window(v["sun"], opt.after_sunrise, opt.before_sunset)
    if window is None:
        return [{"id": "missing_data", "ok": False, "value": None, "limit": None}]
    base = v["comfort"] if base is None else base

    def check(id_: str, ok: bool, value=None, limit=None) -> dict:
        return {"id": id_, "ok": bool(ok), "value": value, "limit": limit}

    minute = now.hour * 60 + now.minute
    # start for at least two steps (1 K), keep while one is still affordable
    first = base + (STEP if active else 2 * STEP)
    tank = need(first, v) + (0 if active else HYSTERESIS)
    if not active and opt.tank_threshold is not None:
        tank = max(tank, opt.tank_threshold)
    target = best(written, base, v, opt)
    # the hot water circuit asks the boiler when its probe falls under its own setpoint
    reserve = max(opt.hot_water_reserve, v["ecs_set"] + 1) - (2 if active else 0)
    room = (written if active else (target or opt.target)) + (0.5 if active else -1)
    where = v.get("presence")
    demand = int(v.get("buffer_state") or 0) & 0x100 or int(v.get("ecs_state") or 0) & 0x4000
    out = [
        check("burner", not v.get("burner") and not demand, 1 if v.get("burner") else 2 if demand else 0),  # 2: asked
        check("occupied", where != "home", where),
        check("far_away", where != "far" or v["top"] >= opt.surplus, v["top"] if where == "far" else None, opt.surplus),
        check("heating_off", v["mode"] != 0 and v["season"] == 1),
        check("outside_window", window[0] <= minute < window[1], minute, list(window)),
        check("cloudy", v["forecast_clouds"] <= v["cloud_limit"], v["forecast_clouds"], v["cloud_limit"]),
        # the circuit would not heat anyway
        check("mild_outdoor", v["outdoor"] < v["heating_limit"], v["outdoor"], v["heating_limit"]),
        check("tank_cold", v["top"] >= tank and (target is not None and target >= first or base >= opt.target), v["top"], round(tank, 1)),
        check("hot_water_low", v["ecs"] >= reserve, v["ecs"], reserve),
        check("room_warm", v["room"] < room and (active or base < opt.target), v["room"], room),
    ]
    if active:  # someone changed the comfort: leave it to them
        out.insert(1, check("manual", abs(v["comfort"] - written) <= 0.01, v["comfort"], written))
    return out


def decide(written: float | None, changed_at: float | None, now: datetime, v: dict, opt: Options,
           base: float | None = None, stepped_at: float | None = None) -> tuple[float | None, str]:
    """(comfort to hold, None for no boost; reason). ``written``: the comfort we set, None when not boosting;
    ``base``: the comfort to put back; ``stepped_at``: when the comfort last changed during this boost."""
    active = written is not None
    base = v.get("comfort") if base is None else base
    reason = next((c["id"] for c in checks(written, now, v, opt, base) if not c["ok"]), None)
    want = reason is None
    if want != active and reason not in URGENT and changed_at is not None and now.timestamp() - changed_at < DWELL:
        return written, "dwell"
    if not want:
        return None, reason
    target = best(written, base, v, opt)
    if not active:
        return base + 2 * STEP, "running"  # start low, then climb
    # down at once, up one step at a time, once the controller answered the last one
    if target > written:
        since = stepped_at if stepped_at is not None else changed_at
        target = written + STEP if since is None or now.timestamp() - since >= STEP_DWELL else written
    return target, "running"
