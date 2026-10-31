"""Check the solar boost decision without Home Assistant, then replay it on the recorded history.

    python3 scripts/backtest_solar_boost.py                                   # logic checks only
    HASS_URL=https://... HASS_TOKEN=... python3 scripts/backtest_solar_boost.py [days]   # + dry run

Offline part: thresholds, hysteresis, burner, manual change, dwell, restart in the middle of a boost.
Dry run (read-only): replays decide() minute by minute on the Pellematic Compact entities that Home
Assistant recorded and lists when the boost would have run, and where the burner starts fell.
The replay sees the house *without* the boost: once it would have started, the real buffer would have
cooled faster than recorded, so durations are optimistic.
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
}


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 31, hour, minute).astimezone()


def offline() -> None:
    opt = sb.Options()
    now = at(13)
    assert sb.decide(None, None, now, SUNNY, opt) == (True, "running")
    # start threshold: worst case 60 + 5 + 1 + 1.5 = 67.5 °C
    assert sb.decide(None, None, now, {**SUNNY, "top": 67.4}, opt) == (False, "tank_cold")
    assert sb.decide(None, None, now, {**SUNNY, "top": 64}, sb.Options(tank_threshold=63)) == (True, "running")
    # running: stops only under the real buffer setpoint + 1 K (hysteresis)
    running = {**SUNNY, "comfort": 24.0, "tank_set": 65.0}
    assert sb.decide(24.0, None, now, {**running, "top": 66.5}, opt) == (True, "running")
    assert sb.decide(24.0, None, now, {**running, "top": 65.5}, opt) == (False, "tank_cold")
    # hot water: start at the reserve, stop 2 K under it; never under its own setpoint + 1 K
    assert sb.decide(None, None, now, {**SUNNY, "ecs": 54.5}, opt)[1] == "hot_water_low"
    assert sb.decide(24.0, None, now, {**running, "ecs": 53.5}, opt) == (True, "running")
    assert sb.decide(24.0, None, now, {**running, "ecs": 52.5}, opt) == (False, "hot_water_low")
    assert sb.decide(None, None, now, {**SUNNY, "ecs_set": 60.0, "ecs": 60.5}, opt)[1] == "hot_water_low"
    # window: sunrise + 120 min to sunset - 90 min
    assert sb.decide(None, None, at(9, 47), SUNNY, opt)[0] and not sb.decide(None, None, at(9, 46), SUNNY, opt)[0]
    assert sb.decide(24.0, None, at(16, 25), running, opt) == (False, "outside_window")
    # room: start under target - 1, stop at target + 0.5
    assert sb.decide(None, None, now, {**SUNNY, "room": 23.2}, opt)[1] == "room_warm"
    assert sb.decide(24.0, None, now, {**running, "room": 24.4}, opt)[0]
    assert sb.decide(24.0, None, now, {**running, "room": 24.5}, opt) == (False, "room_warm")
    assert sb.decide(None, None, now, {**SUNNY, "comfort": 24.0}, opt)[1] == "room_warm"
    # clouds, mild outdoor, heating off, missing values
    assert sb.decide(None, None, now, {**SUNNY, "forecast_clouds": 60}, opt)[1] == "cloudy"
    assert sb.decide(None, None, now, {**SUNNY, "outdoor": 20.0}, opt)[1] == "mild_outdoor"
    assert sb.decide(None, None, now, {**SUNNY, "mode": 0}, opt)[1] == "heating_off"
    assert sb.decide(None, None, now, {**SUNNY, "season": 2}, opt)[1] == "heating_off"
    assert sb.decide(None, None, now, {**SUNNY, "sun": "no sun times"}, opt)[1] == "missing_data"
    assert sb.decide(24.0, None, now, {**running, "room": None}, opt) == (False, "missing_data")
    # dwell: 10 min between changes, except burner / manual / missing data / heating off
    just = now.timestamp() - 300
    assert sb.decide(None, just, now, SUNNY, opt) == (False, "dwell")
    assert sb.decide(24.0, just, now, {**running, "top": 60}, opt) == (True, "dwell")
    assert sb.decide(24.0, just, now, {**running, "burner": 1}, opt) == (False, "burner")
    assert sb.decide(24.0, just, now, {**running, "comfort": 22.0}, opt) == (False, "manual")
    assert sb.decide(None, now.timestamp() - 601, now, SUNNY, opt) == (True, "running")
    # restart in the middle of a boost: the stored target is what we wrote, nothing else changes
    assert sb.decide(24.0, None, now, running, opt) == (True, "running")
    assert sb.decide(24.0, None, now, running, sb.Options(target=25)) == (True, "running")
    # every reason the decision gives is one the panel knows
    for c in sb.checks(24.0, now, running, opt):
        assert c["id"] in sb.REASONS, c
    assert sb.Options.from_dict({"target": 23, "tank_threshold": None, "climates": ["climate.x"]}) == sb.Options(target=23)
    print("hors ligne: seuils, hystérésis, brûleur, consigne manuelle, attente et redémarrage OK")


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
}
# not recorded by the Pellematic integration: the values read on the portal on 31 Oct
FIXED = {"season": 1, "heating_limit": 20.0, "flow_max": 60.0, "overshoot": 5.0}


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


def dry_run(days: int) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    changes = fetch(start, end)
    missing = [n for n in ENTITIES if n not in changes]
    print(f"\nessai à blanc du {start.astimezone():%d/%m %H:%M} au {end.astimezone():%d/%m %H:%M}"
          f" ({', '.join(f'{len(v)} {k}' for k, v in changes.items())}); valeurs fixes: {FIXED}")
    if missing:
        print("  absentes de l'historique:", missing)
    opt = sb.Options()
    cursor = dict.fromkeys(changes, 0)
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
        if written is not None:
            v["comfort"] = written  # what the controller would hold while boosting
        want, reason = sb.decide(written, changed_at, now, v, opt)
        if v.get("burner") == 1 and last_burner == 0:
            window = v.get("sun") and sb.sun_window(v["sun"], opt.after_sunrise, opt.before_sunset)
            inside = bool(window) and window[0] <= now.hour * 60 + now.minute < window[1]
            burner_starts.append((now, written is not None, inside))
        last_burner = v.get("burner")
        if want and written is None:
            written, changed_at = opt.target, ts
            runs.append({"start": now, "top": v["top"]})
        elif not want and written is not None:
            written, changed_at = None, ts
            runs[-1].update(end=now, reason=reason, top_end=v["top"])
        if not want:
            reasons[reason] = reasons.get(reason, 0) + 1
    print(f"  surchauffes simulées: {len(runs)}")
    for run in runs:
        end_text = f"{run['end']:%H:%M} ({run['reason']}, haut {run['top_end']} °C)" if "end" in run else "en cours"
        minutes = ((run.get("end") or datetime.now().astimezone()) - run["start"]).total_seconds() / 60
        print(f"    {run['start']:%a %d/%m %H:%M} -> {end_text}, {minutes:.0f} min, haut au départ {run['top']} °C")
    print(f"  démarrages du brûleur: {len(burner_starts)}")
    for when, during, inside in burner_starts:
        flag = "PENDANT une surchauffe simulée: elle se serait arrêtée" if during else "dans la fenêtre solaire" if inside else "hors fenêtre"
        print(f"    {when:%a %d/%m %H:%M}: {flag}")
    print("  minutes sans surchauffe, par raison:", dict(sorted(reasons.items(), key=lambda kv: -kv[1])))


offline()
if os.environ.get("HASS_URL"):
    dry_run(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
