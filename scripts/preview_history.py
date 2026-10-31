"""Write scripts/preview-history.json (git-ignored) from 48 h of Home Assistant history, for preview.html.

    HASS_URL=https://... HASS_TOKEN=... python3 scripts/preview_history.py

Read-only. Uses the entities of the Pellematic Compact integration, resampled to one point a minute
like the integration's own history (custom_components/okofen_portal/history.py).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
import pathlib
import urllib.parse
import urllib.request

SERIES = {  # names of const.DASHBOARD (the panel reads them by name), then boost
    "tank_top": "sensor.pellematic_buffer_storage_temperature_upper_area",
    "tank_mid": "sensor.pellematic_buffer_storage_temperature_middle_area",
    "tank_bottom": "sensor.pellematic_solar_thermal_buffer_storage_temperature_lower_area",
    "coll": "sensor.pellematic_solar_thermal_collector_temperature",
    "flow": "sensor.pellematic_heating_circuit_1_flow_temperature",
    "room": "sensor.pellematic_heating_circuit_1_room_temperature",
    "outdoor": "sensor.pellematic_outside_temperature",
    "burner": "sensor.pellematic_buffer_storage_state",  # "Demande marche ON": the boiler is asked
    "solar_pump": "sensor.pellematic_solar_thermal_collector_circuit_pump_2",
    "heating_pump": "sensor.pellematic_heating_circuit_1_pump_2",
    "boiler_pump": "sensor.pellematic_buffer_storage_pump_2",
    "ecs_probe": "sensor.pellematic_hot_water_circuit_1_temperature_on",
    "tank_set": "sensor.pellematic_buffer_storage_temperature_upper_area_set",
    "room_set": "sensor.pellematic_heating_circuit_1_room_temperature_set",
    "flow_set": "sensor.pellematic_heating_circuit_1_flow_temperature_set",
    "ecs_set": "sensor.pellematic_hot_water_circuit_1_temperature_set",
    "pool": "sensor.pellematic_solar_thermal_2_buffer_storage_temperature_lower_area",
    "pool_pump": "sensor.pellematic_solar_thermal_2_collector_circuit_pump_2",
}
WEATHER = {  # the sky, as history.WEATHER: from the current clouds and the first forecast string ("...|01d|800|...")
    "clouds": "sensor.pellematic_weather_l_clouds",
    "code": "sensor.pellematic_forecast_l_w_0",
    "icon": "sensor.pellematic_forecast_l_w_0",
}
HOLD = 3 * 3600  # a value is kept this long without a new one (Home Assistant records changes only)


def value(name: str, state: str):
    if name in ("code", "icon"):
        parts = state.split("|")
        if len(parts) < 6:
            return None
        return parts[4] if name == "icon" else int(parts[5]) if parts[5].isdigit() else None
    if name == "burner":
        return 1 if state.endswith("ON") else 0 if state.endswith("OFF") else None
    try:
        return float(state)
    except ValueError:
        return None


def main() -> None:
    end = datetime.now(timezone.utc)
    start = (datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)).astimezone(timezone.utc)
    entities = {**SERIES, **WEATHER}
    query = urllib.parse.urlencode({"filter_entity_id": ",".join(set(entities.values())), "end_time": end.isoformat(), "minimal_response": "", "no_attributes": ""})
    request = urllib.request.Request(
        f"{os.environ['HASS_URL']}/api/history/period/{start.isoformat()}?{query}",
        headers={"Authorization": f"Bearer {os.environ['HASS_TOKEN']}"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        history = json.load(response)
    changes = {}
    for states in history:
        entity = states[0]["entity_id"]
        for name in (k for k, e in entities.items() if e == entity):
            changes[name] = [(datetime.fromisoformat(s["last_changed"]).timestamp(), value(name, s["state"])) for s in states]
    points = []
    cursor = {name: 0 for name in entities}
    for ts in range(int(start.timestamp()), int(end.timestamp()), 60):
        point = [ts]
        for name in [*SERIES, "boost", *WEATHER]:
            if name == "boost":
                point.append(0)
                continue
            items = changes.get(name, [])
            while cursor[name] + 1 < len(items) and items[cursor[name] + 1][0] <= ts:
                cursor[name] += 1
            at, v = items[cursor[name]] if items and items[cursor[name]][0] <= ts else (0, None)
            point.append(v if ts - at <= HOLD or name in ("burner", "solar_pump", "boiler_pump", "pool_pump", "clouds", "code", "icon") else None)
        points.append(point)
    out = pathlib.Path(__file__).parent / "preview-history.json"
    out.write_text(json.dumps({"series": [*SERIES, "boost", *WEATHER], "points": points}))
    print(f"{out}: {len(points)} points, {sum(1 for n in entities if n in changes)}/{len(entities)} series")


main()
