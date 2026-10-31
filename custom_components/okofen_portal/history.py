"""The panel's last 48 h, read from the recorder: the entities of its values, the weather and the solar boost.

Sent to the panel as one point a minute: [unix time, value per SERIES...], None where nothing was recorded.
"""

from __future__ import annotations

import time

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DASHBOARD, DOMAIN, MIXER_STATES

WEATHER = ("clouds", "code", "icon")
SERIES = (*DASHBOARD, "boost", *WEATHER)
KEEP = 48 * 3600
# weather entity condition -> (cloud cover %, OpenWeatherMap code): what the panel's sky reads
SKY = {
    "sunny": (0, 800), "clear-night": (0, 800), "windy": (10, 800), "partlycloudy": (40, 802),
    "windy-variant": (40, 802), "cloudy": (90, 804), "fog": (90, 741), "rainy": (90, 501), "pouring": (90, 502),
    "lightning": (90, 211), "lightning-rainy": (90, 211), "snowy": (90, 601), "snowy-rainy": (90, 611),
    "hail": (90, 611), "exceptional": (50, 781),
}


async def async_points(hass: HomeAssistant, entry_id: str) -> dict:
    """The last 48 h of the panel, from whatever the recorder holds for the enabled entities."""
    out = {"series": list(SERIES), "points": []}
    if "recorder" not in hass.config.components:
        return out
    from homeassistant.components.recorder import get_instance, history  # noqa: PLC0415 (optional)

    registry = er.async_get(hass)

    def find(domain: str, unique_id: str) -> str | None:
        entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)
        return entity_id if entity_id and not registry.async_get(entity_id).disabled else None

    ids = {name: find("sensor", f"{entry_id}_{key}") or find("binary_sensor", f"{entry_id}_{key}") for name, key in DASHBOARD.items()}
    ids["boost"] = find("sensor", f"{entry_id}_solar_boost_state")
    ids["sky"] = find("weather", f"{entry_id}_weather")
    ids = {name: entity_id for name, entity_id in ids.items() if entity_id}
    if not ids:
        return out
    end = time.time()
    start = end - KEEP

    def read() -> list[list]:
        states = history.get_significant_states(
            hass, dt_util.utc_from_timestamp(start), None, list(ids.values()), None, True, False, False, True
        )
        return resample({name: states.get(entity_id, []) for name, entity_id in ids.items()}, start, end)

    out["points"] = await get_instance(hass).async_add_executor_job(read)
    return out


def resample(states: dict[str, list], start: float, end: float) -> list[list]:
    """One point a minute from the recorded changes (each value holds until the next one)."""
    changes = {
        name: [(s.last_changed.timestamp(), _value(name, s)) for s in items if isinstance(s, State)]
        for name, items in states.items()
    }
    cursor = dict.fromkeys(changes, 0)

    def at(name: str, ts: int):
        items = changes.get(name)
        if not items:
            return None
        while cursor[name] + 1 < len(items) and items[cursor[name] + 1][0] <= ts:
            cursor[name] += 1
        return items[cursor[name]][1] if items[cursor[name]][0] <= ts else None

    points = []
    for ts in range(int(start) // 60 * 60 + 60, int(end), 60):
        sky = at("sky", ts)
        points.append([ts, *(at(name, ts) for name in DASHBOARD), at("boost", ts) or 0, *(sky or (None, None)), None])
    return points


def _value(name: str, state: State):
    """A recorded state as the panel reads it."""
    if name == "sky":
        return SKY.get(state.state)
    if name == "boost":
        return 1 if state.state == "active" else 0
    if state.state in ("on", "off"):
        return 1 if state.state == "on" else 0
    if state.state in MIXER_STATES:
        return MIXER_STATES.index(state.state)
    try:
        return float(state.state)
    except ValueError:
        return None  # unavailable, unknown
