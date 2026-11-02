"""Check the panel history read from the recorder (history.py) with a fake registry and recorder.

    .venv/bin/python scripts/check_history.py

Needs the homeassistant package (imports only, no running instance).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import pathlib
import sys
import time
import types

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "custom_components"))
from homeassistant.core import State  # noqa: E402
from okofen_portal import history  # noqa: E402
from okofen_portal.const import DASHBOARD  # noqa: E402

NOW = time.time()
H = 3600


def state(entity_id, value, ago):
    s = State(entity_id, value)
    s.last_changed = datetime.fromtimestamp(NOW - ago, timezone.utc)
    return s


RECORDED = {  # yesterday and today, as the recorder holds them
    "sensor.top": [state("sensor.top", "55.0", 47 * H), state("sensor.top", "unavailable", 25 * H), state("sensor.top", "66.5", 20 * H)],
    "binary_sensor.burner": [state("binary_sensor.burner", "off", 47 * H), state("binary_sensor.burner", "on", 22 * H),
                             state("binary_sensor.burner", "off", 21.5 * H)],
    "sensor.mixer": [state("sensor.mixer", "closing", 30 * H)],
    "sensor.boost": [state("sensor.boost", "waiting", 47 * H), state("sensor.boost", "active", 3 * H)],
    "weather.okofen": [state("weather.okofen", "sunny", 47 * H), state("weather.okofen", "snowy", 5 * H)],
    "sensor.disabled": [state("sensor.disabled", "99", 47 * H)],
}
UNIQUE = {  # unique id -> (entity id, disabled)
    f"e1_{DASHBOARD['tank_top']}": ("sensor.top", False),
    f"e1_{DASHBOARD['burner']}": ("binary_sensor.burner", False),
    f"e1_{DASHBOARD['mixer']}": ("sensor.mixer", False),
    f"e1_{DASHBOARD['coll']}": ("sensor.disabled", True),
    "e1_solar_boost_state": ("sensor.boost", False),
    "e1_weather": ("weather.okofen", False),
}


class Registry:
    def async_get_entity_id(self, domain, platform, unique_id):
        entity_id = UNIQUE.get(unique_id, (None,))[0]
        return entity_id if entity_id and entity_id.startswith(domain + ".") else None

    def async_get(self, entity_id):
        return types.SimpleNamespace(disabled=next(d for e, d in UNIQUE.values() if e == entity_id))


class Recorder:
    async def async_add_executor_job(self, func, *args):
        return func(*args)


asked = []


def significant_states(hass, start, end, entity_ids, *rest):
    asked.extend(entity_ids)
    return {e: RECORDED[e] for e in entity_ids}


history.er = types.SimpleNamespace(async_get=lambda hass: Registry())
sys.modules["homeassistant.components.recorder"] = types.SimpleNamespace(
    get_instance=lambda hass: Recorder(),
    history=types.SimpleNamespace(
        get_significant_states=significant_states,
        state_changes_during_period=lambda hass, start, end, entity_id, *rest: {entity_id: RECORDED[entity_id][:1]},
    ),
)
hass = types.SimpleNamespace(config=types.SimpleNamespace(components={"recorder"}))
out = asyncio.run(history.async_points(hass, "e1"))
i = {name: n + 1 for n, name in enumerate(out["series"])}
points = out["points"]
assert out["series"] == list(history.SERIES) and "sensor.disabled" not in asked, asked
assert 2870 < len(points) <= 2880 and all(a[0] + 60 == b[0] for a, b in zip(points, points[1:])), len(points)
assert all(len(p) == len(history.SERIES) + 1 for p in points)
at = lambda ago: min(points, key=lambda p: abs(p[0] - (NOW - ago * H)))
assert at(30)[i["tank_top"]] == 55.0 and at(24)[i["tank_top"]] is None and at(10)[i["tank_top"]] == 66.5
assert at(21.8)[i["burner"]] == 1 and at(21)[i["burner"]] == 0 and at(23)[i["burner"]] == 0
assert at(10)[i["mixer"]] == 2 and at(40)[i["mixer"]] is None
assert at(10)[i["coll"]] is None, "disabled entity not read"
assert at(10)[i["boost"]] == 0 and at(1)[i["boost"]] == 1
assert (at(10)[i["clouds"]], at(10)[i["code"]]) == (0, 800) and (at(1)[i["clouds"]], at(1)[i["code"]]) == (90, 601)
assert abs(out["first"] - (NOW - 47 * H)) < 1, "first recorded state"
day = asyncio.run(history.async_points(hass, "e1", NOW - 30 * H, NOW - 20 * H))["points"]  # a window asked by the panel
assert 595 < len(day) <= 600 and day[0][0] >= NOW - 30 * H and day[-1][0] < NOW - 20 * H, len(day)
assert asyncio.run(history.async_points(types.SimpleNamespace(config=types.SimpleNamespace(components=set())), "e1"))["points"] == []
print("historique du panneau lu depuis le recorder: valeurs, brûleur, vanne, surchauffe, ciel, entités désactivées: OK")

# the inertia learnt from the hourly statistics: room mean, highest setpoint of the hour, outdoor and flow means
for name in history.LEARN_KEYS:
    UNIQUE[f"e1_{DASHBOARD[name]}"] = (f"sensor.{name}", False)
stats_asked, seen = [], []
T0 = 1_800_000_000  # a whole hour


def statistics_during_period(hass, start, end, ids, period, units, types_):
    stats_asked.append((set(ids), period, types_))
    row = lambda i, mean, high: {"start": T0 + i * H, "mean": mean, "max": high}  # noqa: E731
    return {"sensor.room": [row(0, 19.5, 19.6), row(1, 19.8, 20)], "sensor.room_set": [row(0, 8, 8), row(1, 14, 20)],
            "sensor.outdoor": [row(0, 4, 5), row(1, 4, 5)], "sensor.flow": [row(0, 22, 23)]}  # flow missing for the 2nd hour


sys.modules["homeassistant.components.recorder.statistics"] = types.SimpleNamespace(statistics_during_period=statistics_during_period)
history.learn = lambda rows: seen.extend(rows) or {"state": "learning"}
assert asyncio.run(history.async_learning(hass, "e1")) == {"state": "learning"}
assert stats_asked == [({"sensor.room", "sensor.room_set", "sensor.outdoor", "sensor.flow"}, "hour", {"mean", "max"})], stats_asked
assert [(h.ts, h.room, h.set, h.out, h.flow) for h in seen] == [(T0, 19.5, 8, 4, 22)], seen  # set = max, incomplete hour left out
print("apprentissage de l'inertie lu depuis les statistiques horaires: OK")
