"""The last 48 h of the panel's values, one point a minute, for its history tab (does not need the recorder)."""

from __future__ import annotations

from datetime import timedelta
import time

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import DASHBOARD, DOMAIN
from .weather_parse import panel_weather

# every value the panel draws (const.DASHBOARD) and its sky, so the schematic can be replayed; boost: 1 while it runs
WEATHER = ("clouds", "code", "icon")
SERIES = (*DASHBOARD, "boost", *WEATHER)
KEEP = 48 * 3600


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

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
        await self._store.async_save(self._data())

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
