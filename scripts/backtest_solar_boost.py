"""Check the solar boost decision without Home Assistant, then replay it on the recorded history.

    python3 scripts/backtest_solar_boost.py                                   # logic checks only
    HASS_URL=https://... HASS_TOKEN=... python3 scripts/backtest_solar_boost.py [days]   # + dry run

Offline part: thresholds, hysteresis, burner, manual change, dwell, restart in the middle of a boost.
Dry run (read-only): replays decide() minute by minute on the Pellematic Compact entities that Home
Assistant recorded, with the people's positions and the alarm, and lists when the boost would have run,
how high the comfort would have climbed, and where the burner starts fell.
The replay sees the house *without* the boost: once it would have started, the real buffer would have
cooled faster than recorded, so durations are optimistic, and the controller's answer to each step
(its buffer setpoint) is the recorded one, not the one the higher comfort would have made: the curve decides.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
import json
import os
import pathlib
import sys
import types
import urllib.parse
import urllib.request

root = pathlib.Path(__file__).parent.parent / "custom_components/okofen_portal"
pkg = types.ModuleType("okofen_portal")
pkg.__path__ = [str(root)]
sys.modules["okofen_portal"] = pkg
sb = importlib.import_module("okofen_portal.solar_boost")

SUNNY = {  # 13:00 on a sunny autumn day, buffer hot, nothing in the way
    "top": 68.0, "tank_set": 8.0, "ecs": 66.0, "ecs_set": 50.0, "room": 21.0, "comfort": 20.0, "mode": 1,
    "season": 1, "outdoor": 12.0, "heating_limit": 20.0, "flow_max": 60.0, "overshoot": 5.0,
    "forecast_clouds": 10, "cloud_limit": 55, "burner": 0, "sun": "sam., 31 oct. 13:00|15|0|9 km/h|01d|800|C|07:47|17:51",
    "room_set": 20.0, "curve_foot": 35.0, "curve_slope": 1.4,
}
HOME = (47.25, -1.45)


def on(written: float, v: dict) -> dict:
    """The values while boosting at ``written``: the controller holds it (no remote offset here)."""
    return {**v, "comfort": written, "room_set": written}


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 31, hour, minute).astimezone()


def offline() -> None:
    opt = sb.Options()
    now = at(13)
    t = now.timestamp()
    # the buffer the controller asks for: curve 35 + 1.4 x (comfort - outdoor) + 8 K catch-up, capped at 60, + 5 + 1
    assert round(sb.need(21, SUNNY), 1) == 61.6 and round(sb.need(24, SUNNY), 1) == 65.8 and sb.need(30, SUNNY) == 66
    assert round(sb.need(21, {**SUNNY, "room_set": 18.5}), 1) == 59.5  # the controller's offset (remote -1.5 K) counts
    # start one step above +0.5 K: comfort + 1 K, when the buffer holds it with the hysteresis
    assert sb.decide(None, None, now, SUNNY, opt) == (21.0, "running")
    assert sb.decide(None, None, now, {**SUNNY, "top": 63.0}, opt) == (None, "tank_cold")
    assert sb.decide(None, None, now, {**SUNNY, "top": 63.2, "room": 19.5}, opt) == (21.0, "running")
    assert sb.decide(None, None, now, {**SUNNY, "top": 63.2}, opt) == (None, "room_warm")  # 21 °C reachable, room already there
    assert sb.decide(None, None, now, {**SUNNY, "top": 64}, sb.Options(tank_threshold=66)) == (None, "tank_cold")
    # climbing: one step once the controller answered (2 min), up to the target, as far as the buffer holds
    assert sb.decide(21.0, None, now, on(21.0, SUNNY), opt, 20.0) == (21.5, "running")
    assert sb.decide(21.0, t - 600, now, on(21.0, SUNNY), opt, 20.0, t - 60) == (21.0, "running")
    assert sb.decide(21.0, t - 600, now, on(21.0, SUNNY), opt, 20.0, t - 121) == (21.5, "running")
    assert sb.decide(23.5, None, now, on(23.5, {**SUNNY, "top": 66.0}), opt, 20.0) == (24.0, "running")
    assert sb.decide(24.0, None, now, on(24.0, {**SUNNY, "top": 66.0}), opt, 20.0) == (24.0, "running")
    # down at once: the buffer cooled, or the controller asks more than it holds (its real setpoint + 1 K)
    assert sb.decide(24.0, t - 60, now, on(24.0, {**SUNNY, "top": 64.5}), opt, 20.0, t - 10) == (23.0, "running")
    assert sb.decide(22.0, t - 60, now, on(22.0, {**SUNNY, "top": 64.0, "tank_set": 63.5}), opt, 20.0, t - 10) == (21.5, "running")
    # stop when not even +0.5 K is held, at once (the boiler would start)
    assert sb.decide(21.0, t - 60, now, on(21.0, {**SUNNY, "top": 60.5}), opt, 20.0) == (None, "tank_cold")
    assert sb.decide(20.5, t - 60, now, on(20.5, {**SUNNY, "top": 64.0, "tank_set": 63.5}), opt, 20.0) == (None, "tank_cold")
    running = on(22.0, {**SUNNY, "tank_set": 60.0})
    # hot water: start at the reserve, stop 2 K under it; never under its own setpoint + 1 K
    assert sb.decide(None, None, now, {**SUNNY, "ecs": 54.5}, opt)[1] == "hot_water_low"
    assert sb.decide(22.0, None, now, {**running, "ecs": 53.5}, opt, 20.0)[0] is not None
    assert sb.decide(22.0, t - 60, now, {**running, "ecs": 52.5}, opt, 20.0) == (None, "hot_water_low")
    assert sb.decide(None, None, now, {**SUNNY, "ecs_set": 60.0, "ecs": 60.5}, opt)[1] == "hot_water_low"
    # window: sunrise + 120 min to sunset - 90 min
    assert sb.decide(None, None, at(9, 47), SUNNY, opt)[0] and not sb.decide(None, None, at(9, 46), SUNNY, opt)[0]
    assert sb.decide(22.0, None, at(16, 25), running, opt, 20.0) == (None, "outside_window")
    # room: start under the reachable target - 1, stop at what we wrote + 0.5
    assert sb.decide(None, None, now, {**SUNNY, "room": 23.2}, opt)[1] == "room_warm"
    assert sb.decide(22.0, None, now, {**running, "room": 22.4}, opt, 20.0)[0]
    assert sb.decide(22.0, None, now, {**running, "room": 22.5}, opt, 20.0) == (None, "room_warm")
    assert sb.decide(None, None, now, {**SUNNY, "comfort": 24.0, "room_set": 24.0}, opt)[1] == "room_warm"
    # clouds, mild outdoor, heating off, missing values
    assert sb.decide(None, None, now, {**SUNNY, "forecast_clouds": 60}, opt)[1] == "cloudy"
    assert sb.decide(None, None, now, {**SUNNY, "outdoor": 20.0}, opt)[1] == "mild_outdoor"
    assert sb.decide(None, None, now, {**SUNNY, "mode": 0}, opt)[1] == "heating_off"
    assert sb.decide(None, None, now, {**SUNNY, "season": 2}, opt)[1] == "heating_off"
    assert sb.decide(None, None, now, {**SUNNY, "sun": "no sun times"}, opt)[1] == "missing_data"
    assert sb.decide(None, None, now, {**SUNNY, "curve_slope": None}, opt)[1] == "missing_data"
    assert sb.decide(22.0, None, now, {**running, "room": None}, opt, 20.0) == (None, "missing_data")
    # presence: someone home, no boost and a running one stops at once; everyone far, only the surplus
    assert sb.decide(None, None, now, {**SUNNY, "presence": "home"}, opt) == (None, "occupied")
    assert sb.decide(22.0, t - 60, now, {**running, "presence": "home"}, opt, 20.0) == (None, "occupied")
    assert sb.decide(None, None, now, {**SUNNY, "presence": "near"}, opt) == (21.0, "running")
    assert sb.decide(None, None, now, {**SUNNY, "presence": "far"}, opt) == (None, "far_away")
    assert sb.decide(None, None, now, {**SUNNY, "presence": "far", "top": 81.0}, opt) == (21.0, "running")
    assert sb.presence("disarmed", [("not_home", 47.3, -1.4), ("home", *HOME)], HOME, 30) == "home"
    assert sb.presence("armed_night", [("not_home", 48.85, 2.35)], HOME, 30) == "home"
    assert sb.presence("armed_away", [("home", *HOME)], HOME, 30) == "near"  # a phone not updated yet
    assert sb.presence(None, [("not_home", 47.3, -1.4), ("not_home", 48.85, 2.35)], HOME, 30) == "near"  # the nearest
    assert sb.presence(None, [("not_home", 48.85, 2.35)], HOME, 30) == "far"  # Paris, ~340 km
    assert sb.presence("armed_away", [], HOME, 30) == "near" and sb.presence(None, [("unknown", None, None)], HOME, 30) is None
    assert sb.presence(None, [("not_home", None, None)], HOME, 30) == "near"  # away, distance unknown
    # dwell: 10 min before starting again; stops for the boiler, the hot water, presence or a manual change at once
    just = t - 300
    assert sb.decide(None, just, now, SUNNY, opt) == (None, "dwell")
    assert sb.decide(22.0, just, now, {**running, "forecast_clouds": 60}, opt, 20.0) == (22.0, "dwell")
    assert sb.decide(22.0, just, now, {**running, "burner": 1}, opt, 20.0) == (None, "burner")
    assert sb.decide(22.0, just, now, {**running, "comfort": 22.5}, opt, 20.0) == (None, "manual")
    assert sb.decide(None, t - 601, now, SUNNY, opt) == (21.0, "running")
    # restart in the middle of a boost: the stored target is what we wrote, it carries on climbing from there
    assert sb.decide(22.0, None, now, running, opt, 20.0) == (22.5, "running")
    # every reason the decision gives is one the panel knows
    for c in sb.checks(22.0, now, {**running, "presence": "far"}, opt, 20.0):
        assert c["id"] in sb.REASONS, c
    assert sb.Options.from_dict({"target": 23, "tank_threshold": None, "climates": ["climate.x"], "persons": ["person.a"], "far_km": 10}) == sb.Options(target=23, far_km=10)
    print("hors ligne: courbe, cible adaptative (montée, descente, arrêt), présence, eau chaude, attente et redémarrage OK")


# ---------- dry run on the Home Assistant history ----------
ENTITIES = {
    "top": "sensor.pellematic_buffer_storage_temperature_upper_area",
    "tank_set": "sensor.pellematic_buffer_storage_temperature_upper_area_set",
    "ecs": "sensor.pellematic_hot_water_circuit_1_temperature_on",
    "ecs_set": "sensor.pellematic_hot_water_circuit_1_temperature_set",
    "room": "sensor.pellematic_heating_circuit_1_room_temperature",
    "comfort": "number.pellematic_heating_circuit_1_heat_temp",
    "mode": "select.pellematic_heating_circuit_1_mode_auto",  # "1_auto": the leading number
    "outdoor": "sensor.pellematic_outside_temperature",
    "forecast_clouds": "sensor.pellematic_weather_l_forecast_clouds",
    "cloud_limit": "number.pellematic_weather_cloud_limit",
    "burner": "sensor.pellematic_buffer_storage_state",  # "Demande marche ON": the boiler is asked
    "sun": "sensor.pellematic_forecast_l_w_0",
    "room_set": "sensor.pellematic_heating_circuit_1_room_temperature_set",
}
# not recorded by the Pellematic integration: the values read on the portal on 31 Oct
FIXED = {"season": 1, "heating_limit": 20.0, "flow_max": 60.0, "overshoot": 5.0, "curve_foot": 35.0, "curve_slope": 1.4}
# presence, with their positions (BACKTEST_PERSONS / BACKTEST_ALARM to replay other ones)
PERSONS = [e for e in os.environ.get("BACKTEST_PERSONS", "person.adelamarre,person.cedric").split(",") if e]
ALARM = os.environ.get("BACKTEST_ALARM", "alarm_control_panel.ajax_alarm_thouare")


def parse(name: str, state: str):
    if state in ("unknown", "unavailable", ""):
        return None
    if name == "sun":
        return state
    if name == "burner":
        return 1 if state.endswith("ON") else 0
    if name == "mode":
        return int(state.split("_")[0]) if state[:1].isdigit() else None
    try:
        return float(state)
    except ValueError:
        return None


def fetch(start: datetime, end: datetime) -> dict[str, list[tuple[float, object]]]:
    query = urllib.parse.urlencode(
        {"filter_entity_id": ",".join(ENTITIES.values()), "end_time": end.isoformat(), "minimal_response": "", "no_attributes": ""}
    )
    request = urllib.request.Request(
        f"{os.environ['HASS_URL']}/api/history/period/{start.isoformat()}?{query}",
        headers={"Authorization": f"Bearer {os.environ['HASS_TOKEN']}"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        history = json.load(response)
    out = {}
    for states in history:
        name = next(k for k, e in ENTITIES.items() if e == states[0]["entity_id"])
        out[name] = [(datetime.fromisoformat(s["last_changed"]).timestamp(), parse(name, s["state"])) for s in states]
    return out


def fetch_presence(start: datetime, end: datetime) -> tuple[dict[str, list], tuple[float, float] | None]:
    """(entity -> [(time, state, latitude, longitude)], home position): the people with their positions, the alarm."""
    def get(path: str):
        request = urllib.request.Request(f"{os.environ['HASS_URL']}{path}", headers={"Authorization": f"Bearer {os.environ['HASS_TOKEN']}"})
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    if not [*PERSONS, *filter(None, [ALARM])]:
        return {}, None  # presence not replayed
    query = urllib.parse.urlencode({"filter_entity_id": ",".join([*PERSONS, *filter(None, [ALARM])]), "end_time": end.isoformat()})
    out = {}
    for states in get(f"/api/history/period/{start.isoformat()}?{query}"):
        out[states[0]["entity_id"]] = [
            (datetime.fromisoformat(s["last_updated"]).timestamp(), s["state"], s["attributes"].get("latitude"), s["attributes"].get("longitude"))
            for s in states
        ]
    config = get("/api/config")
    return out, (config["latitude"], config["longitude"])


def dry_run(days: int) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    changes = fetch(start, end)
    people, home = fetch_presence(start, end)
    missing = [n for n in ENTITIES if n not in changes]
    print(f"\nessai à blanc du {start.astimezone():%d/%m %H:%M} au {end.astimezone():%d/%m %H:%M}"
          f" ({', '.join(f'{len(v)} {k}' for k, v in changes.items())}); valeurs fixes: {FIXED}")
    if missing:
        print("  absentes de l'historique:", missing)
    print(f"  présence: {', '.join(f'{len(v)} {k}' for k, v in people.items())}")
    opt = sb.Options()
    cursor = dict.fromkeys(changes, 0)
    seen = dict.fromkeys(people, 0)

    def now_of(entity_id: str, ts: int):
        items = people.get(entity_id, [])
        if not items:
            return None
        while seen[entity_id] + 1 < len(items) and items[seen[entity_id] + 1][0] <= ts:
            seen[entity_id] += 1
        return items[seen[entity_id]] if items and items[seen[entity_id]][0] <= ts else None
    base = stepped = None
    per_day: dict[str, dict] = {}
    written = changed_at = None
    runs: list[dict] = []
    burner_starts: list[tuple[datetime, bool, bool]] = []  # (time, during a simulated boost, inside the sun window)
    last_burner = None
    reasons: dict[str, int] = {}
    for ts in range(int(start.timestamp()), int(end.timestamp()), 60):
        v = dict(FIXED)
        for name, items in changes.items():
            while cursor[name] + 1 < len(items) and items[cursor[name] + 1][0] <= ts:
                cursor[name] += 1
            v[name] = items[cursor[name]][1] if items[cursor[name]][0] <= ts else None
        now = datetime.fromtimestamp(ts).astimezone()
        alarm = now_of(ALARM, ts)
        v["presence"] = sb.presence(alarm[1] if alarm else None, [p[1:] for e in PERSONS if (p := now_of(e, ts))], home, opt.far_km)
        if written is not None:
            # what the controller would hold while boosting, with its own offset kept
            if v.get("room_set") is not None and v.get("comfort") is not None and v["room_set"] > 8:
                v["room_set"] += written - v["comfort"]
            v["comfort"] = written
        target, reason = sb.decide(written, changed_at, now, v, opt, base, stepped)
        want = target is not None
        day = per_day.setdefault(f"{now:%a %d/%m}", {"boost": 0, "max": None, "presence": {}})
        day["presence"][v["presence"]] = day["presence"].get(v["presence"], 0) + 1
        if v.get("burner") == 1 and last_burner == 0:
            window = v.get("sun") and sb.sun_window(v["sun"], opt.after_sunrise, opt.before_sunset)
            inside = bool(window) and window[0] <= now.hour * 60 + now.minute < window[1]
            burner_starts.append((now, written is not None, inside))
        last_burner = v.get("burner")
        if want and written is None:
            written, changed_at, base, stepped = target, ts, v["comfort"], None
            runs.append({"start": now, "top": v["top"], "max": target, "base": base})
        elif want and target != written:
            written, stepped = target, ts
            runs[-1]["max"] = max(runs[-1]["max"], target)
        elif not want and written is not None:
            written, changed_at, base = None, ts, None
            runs[-1].update(end=now, reason=reason, top_end=v["top"])
        if want:
            day["boost"] += 1
            day["max"] = max(day["max"] or 0, target)
        if not want:
            reasons[reason] = reasons.get(reason, 0) + 1
    print(f"  surchauffes simulées: {len(runs)}")
    for run in runs:
        end_text = f"{run['end']:%H:%M} ({run['reason']}, haut {run['top_end']} °C)" if "end" in run else "en cours"
        minutes = ((run.get("end") or datetime.now().astimezone()) - run["start"]).total_seconds() / 60
        print(f"    {run['start']:%a %d/%m %H:%M} -> {end_text}, {minutes:.0f} min, haut au départ {run['top']} °C, confort {run['base']} -> jusqu'à {run['max']} °C")
    print(f"  démarrages du brûleur: {len(burner_starts)}")
    for when, during, inside in burner_starts:
        flag = "PENDANT une surchauffe simulée: elle se serait arrêtée" if during else "dans la fenêtre solaire" if inside else "hors fenêtre"
        print(f"    {when:%a %d/%m %H:%M}: {flag}")
    print("  minutes sans surchauffe, par raison:", dict(sorted(reasons.items(), key=lambda kv: -kv[1])))
    print("  par jour: minutes de surchauffe, confort le plus haut, présence (minutes)")
    for name, day in per_day.items():
        print(f"    {name}: {day['boost']:4} min, {day['max'] or '–':>5}, {day['presence']}")


offline()
if os.environ.get("HASS_URL"):
    dry_run(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
