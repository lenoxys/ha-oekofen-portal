"""Check that the panel history is filled from the recorder where the integration has no points yet.

    .venv/bin/python scripts/check_history.py

Fake Home Assistant, entity registry and recorder; needs the homeassistant package (imports only).
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
    "sensor.okofen_tank_top": [state("sensor.okofen_tank_top", "55.0", 47 * H), state("sensor.okofen_tank_top", "66.5", 20 * H)],
    "binary_sensor.okofen_burner": [state("binary_sensor.okofen_burner", "off", 47 * H), state("binary_sensor.okofen_burner", "on", 22 * H),
                                    state("binary_sensor.okofen_burner", "off", 21.5 * H)],
    "sensor.okofen_mixer": [state("sensor.okofen_mixer", "closing", 30 * H)],
}
ENTITY = {DASHBOARD["tank_top"]: "sensor.okofen_tank_top", DASHBOARD["burner"]: "binary_sensor.okofen_burner", DASHBOARD["mixer"]: "sensor.okofen_mixer"}


class Registry:
    def async_get_entity_id(self, domain, platform, unique_id):
        entity_id = ENTITY.get(unique_id.removeprefix("e1_"))
        return entity_id if entity_id and entity_id.startswith(domain + ".") else None

    def async_get(self, entity_id):
        return types.SimpleNamespace(disabled=False)


history.er = types.SimpleNamespace(async_get=lambda hass: Registry())


class Recorder:
    async def async_add_executor_job(self, func, *args):
        return func(*args)


def significant_states(hass, start, end, entity_ids, *rest):
    assert end.timestamp() <= NOW + 1
    return {e: RECORDED[e] for e in entity_ids}


sys.modules["homeassistant.components.recorder"] = types.SimpleNamespace(
    get_instance=lambda hass: Recorder(), history=types.SimpleNamespace(get_significant_states=significant_states)
)
saved = []
hass = types.SimpleNamespace(config=types.SimpleNamespace(components={"recorder"}))
entry = types.SimpleNamespace(entry_id="e1")
h = history.History.__new__(history.History)
h.hass, h.entry = hass, entry
h._store = types.SimpleNamespace(async_delay_save=lambda data, delay: saved.append(delay))
own = [int(NOW) - 300, *[None] * (len(history.SERIES))]  # the integration's own first point, 5 min ago
h.points = [own]
asyncio.run(h._async_backfill())
i = {name: n + 1 for n, name in enumerate(history.SERIES)}
assert h.points[-1] is own and all(a[0] < b[0] for a, b in zip(h.points, h.points[1:])), "sorted, own points kept"
assert len(h.points) > 2800 and saved, len(h.points)
at = lambda ago: min(h.points, key=lambda p: abs(p[0] - (NOW - ago * H)))
assert at(30)[i["tank_top"]] == 55.0 and at(10)[i["tank_top"]] == 66.5
assert at(21.8)[i["burner"]] == 1 and at(21)[i["burner"]] == 0 and at(23)[i["burner"]] == 0
assert at(10)[i["mixer"]] == 2 and at(40)[i["mixer"]] is None
assert at(10)[i["coll"]] is None and at(10)[i["boost"]] == 0
print("historique complété depuis le recorder: valeurs, brûleur, vanne, ordre: OK")
