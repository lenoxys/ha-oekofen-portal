"""Solar boost: raise the comfort setpoint on sunny days to heat the house with the buffer's surplus.

ÖkoFEN's own solar discharge cannot do it (it starts at 82 °C, knows neither the hot water reserve
nor the sunset, and does not open the radiator heads). This module only decides; ``boost.py`` writes.
Does not import Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime

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
}
COMFORT_KEY = KEYS["comfort"]
DWELL = 600  # s between two changes, except to stop for the burner, a manual change or missing data
HYSTERESIS = 1.5  # K between the start and stop thresholds
URGENT = {"burner", "manual", "missing_data", "heating_off"}
REASONS = (
    "running", "disabled", "missing_data", "burner", "manual", "heating_off", "outside_window",
    "cloudy", "mild_outdoor", "tank_cold", "hot_water_low", "room_warm", "dwell",
)


@dataclass
class Options:
    target: float = 24  # comfort setpoint written while boosting, °C
    tank_threshold: float | None = None  # buffer top to start; None: worst case (flow max + overshoot + 1 K + hysteresis)
    hot_water_reserve: float = 55  # hot water probe kept above this, °C
    after_sunrise: int = 120  # minutes
    before_sunset: int = 90

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


def checks(written: float | None, now: datetime, v: dict, opt: Options) -> list[dict]:
    """Every condition, in order: ``id`` is the reason when it fails; ``value`` and ``limit`` are for the panel.

    ``written``: the comfort we set, None when not boosting (start thresholds, otherwise stop thresholds).
    """
    active = written is not None
    window = None if any(v.get(k) is None for k in KEYS) else sun_window(v["sun"], opt.after_sunrise, opt.before_sunset)
    if window is None:
        return [{"id": "missing_data", "ok": False, "value": None, "limit": None}]

    def check(id_: str, ok: bool, value=None, limit=None) -> dict:
        return {"id": id_, "ok": bool(ok), "value": value, "limit": limit}

    minute = now.hour * 60 + now.minute
    # raising the comfort raises the buffer setpoint: start only above the worst case, stop just above the real one
    if active:
        tank = v["tank_set"] + 1
    else:
        tank = opt.tank_threshold if opt.tank_threshold is not None else v["flow_max"] + v["overshoot"] + 1 + HYSTERESIS
    # the hot water circuit asks the boiler when its probe falls under its own setpoint
    reserve = max(opt.hot_water_reserve, v["ecs_set"] + 1) - (2 if active else 0)
    room = opt.target + 0.5 if active else opt.target - 1
    out = [
        check("burner", not v["burner"], v["burner"]),
        check("heating_off", v["mode"] != 0 and v["season"] == 1),
        check("outside_window", window[0] <= minute < window[1], minute, list(window)),
        check("cloudy", v["forecast_clouds"] <= v["cloud_limit"], v["forecast_clouds"], v["cloud_limit"]),
        # the circuit would not heat anyway
        check("mild_outdoor", v["outdoor"] < v["heating_limit"], v["outdoor"], v["heating_limit"]),
        check("tank_cold", v["top"] >= tank, v["top"], tank),
        check("hot_water_low", v["ecs"] >= reserve, v["ecs"], reserve),
        check("room_warm", v["room"] < room and (active or v["comfort"] < opt.target), v["room"], room),
    ]
    if active:  # someone changed the comfort: leave it to them
        out.insert(1, check("manual", abs(v["comfort"] - written) <= 0.01, v["comfort"], written))
    return out


def decide(written: float | None, changed_at: float | None, now: datetime, v: dict, opt: Options) -> tuple[bool, str]:
    """(boost wanted, reason). ``written``: the comfort we set, None when not boosting; ``v``: short name -> value."""
    active = written is not None
    reason = next((c["id"] for c in checks(written, now, v, opt) if not c["ok"]), None)
    want = reason is None
    if want != active and reason not in URGENT and changed_at is not None and now.timestamp() - changed_at < DWELL:
        return active, "dwell"
    return want, reason or "running"
