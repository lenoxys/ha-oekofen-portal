"""The last 48 h of the panel's values, one point a minute, for its replay bar and history tab.

Recorded by the integration itself (no entity needs to be enabled). At start, the part of the 48 h it has
not recorded yet (just installed, or Home Assistant was stopped) is filled from the recorder, for the
panel values whose entity is enabled.
"""

from __future__ import annotations

from datetime import timedelta
import logging
import time

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DASHBOARD, DOMAIN, MIXER_STATES
from .weather_parse import panel_weather

# every value the panel draws (const.DASHBOARD) and its sky, so the schematic can be replayed; boost: 1 while it runs
WEATHER = ("clouds", "code", "icon")
SERIES = (*DASHBOARD, "boost", *WEATHER)
KEEP = 48 * 3600
_LOGGER = logging.getLogger(__name__)


class History:
    """Points are [unix time, value per SERIES...]; None where the value was not read."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.points: list[list] = []
        self._store: Store = Store(hass, 1, f"{DOMAIN}_history_{entry.entry_id}")
        self._unsub = None

    async def async_start(self) -> None:
        stored = await self._store.async_load()
        if stored and stored.get("series") == list(SERIES):  # dropped if the recorded values change
            self.points = stored["points"]
        self._unsub = async_track_time_interval(self.hass, self._sample, timedelta(minutes=1))
        self.entry.async_create_background_task(self.hass, self._async_backfill(), f"{DOMAIN} history backfill")

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
        await self._store.async_save(self._data())

    async def _async_backfill(self) -> None:
        """Fill the start of the 48 h from the recorder, where the integration has no points of its own."""
        if "recorder" not in self.hass.config.components:
            return
        from homeassistant.components.recorder import get_instance, history  # noqa: PLC0415 (optional dependency)

        now = time.time()
        start, end = now - KEEP, self.points[0][0] if self.points else now
        if end - start < 600:
            return
        registry = er.async_get(self.hass)
        ids = {}  # panel name -> entity id, for the enabled entities of the panel values
        for name, key in DASHBOARD.items():
            for domain in ("sensor", "binary_sensor"):
                entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{self.entry.entry_id}_{key}")
                if entity_id and not registry.async_get(entity_id).disabled:
                    ids[name] = entity_id
        if not ids:
            return
        try:
            states = await get_instance(self.hass).async_add_executor_job(
                history.get_significant_states, self.hass, dt_util.utc_from_timestamp(start),
                dt_util.utc_from_timestamp(end), list(ids.values()), None, True, False, False, True,
            )
        except Exception as err:  # noqa: BLE001 - the panel works without it
            _LOGGER.debug("History backfill from the recorder failed: %s", err)
            return
        changes = {name: [(s.last_changed.timestamp(), _value(s)) for s in states.get(entity_id, []) if isinstance(s, State)]
                   for name, entity_id in ids.items()}
        cursor = dict.fromkeys(changes, 0)
        filled = []
        for ts in range(int(start) // 60 * 60, int(end) - 59, 60):
            point: list = [ts]
            for name in DASHBOARD:
                items = changes.get(name) or []
                while cursor.get(name, 0) + 1 < len(items) and items[cursor[name] + 1][0] <= ts:
                    cursor[name] += 1
                point.append(items[cursor[name]][1] if items and items[cursor[name]][0] <= ts else None)
            point.append(0)  # boost: not known from the recorder
            point.extend([None] * len(WEATHER))  # sky: the replay shows the current one
            filled.append(point)
        if any(v is not None for p in filled for v in p[1:]):
            self.points[:0] = [p for p in filled if not self.points or p[0] < self.points[0][0]]
            self._store.async_delay_save(self._data, 600)
            _LOGGER.debug("History backfilled from the recorder: %s points, %s values", len(filled), len(ids))

    def _data(self) -> dict:
        return {"series": list(SERIES), "points": self.points}

    @callback
    def _sample(self, _now) -> None:
        data = self.entry.runtime_data
        now = time.time()
        point: list = [round(now)]
        for name in DASHBOARD:
            reading = data.reading(DASHBOARD[name]) if data.fast.last_update_success else None
            point.append(None if reading is None else reading.value)
        point.append(1 if data.boost and data.boost.state == "active" else 0)
        weather = panel_weather({**data.slow.data, **data.fast.data})
        point.extend(weather[name] for name in WEATHER)
        self.points.append(point)
        while self.points and self.points[0][0] < now - KEEP:
            self.points.pop(0)
        self._store.async_delay_save(self._data, 600)


def _value(state: State):
    """A recorded state as the number the panel reads: on / off as 1 / 0, the mixing valve as its index."""
    if state.state in ("on", "off"):
        return 1 if state.state == "on" else 0
    if state.state in MIXER_STATES:
        return MIXER_STATES.index(state.state)
    try:
        return float(state.state)
    except ValueError:
        return None  # unavailable, unknown
