"""Event entity: the burner of the existing boiler starting and stopping."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import OekofenConfigEntry
from .const import CURATED
from .coordinator import OekofenCoordinator
from .entity import OekofenEntity, visible

BURNER_KEY = "LOCAL.L_ke_brennerkontakt_1"
BOILER_TEMP_KEY = "LOCAL.L_ke_temp_ist"


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """One burner event entity, if the controller has an existing boiler."""
    data = entry.runtime_data
    if BURNER_KEY in data.fast.data and visible(data, BURNER_KEY):
        async_add_entities([OekofenBurnerEvent(data.fast)])


class OekofenBurnerEvent(OekofenEntity, EventEntity):
    """Fires ``started`` and ``stopped`` when the burner contact changes (seen at the 30 s poll)."""

    _attr_translation_key = "burner_event"
    _attr_event_types = ["started", "stopped"]

    def __init__(self, coordinator: OekofenCoordinator) -> None:
        super().__init__(coordinator, BURNER_KEY)
        self._attr_unique_id = f"{self._attr_unique_id}_event"
        self._on: bool | None = None
        self._since = None

    @callback
    def _handle_coordinator_update(self) -> None:
        reading = self.coordinator.data.get(BURNER_KEY)
        if reading is not None:
            on, now = bool(reading.value), dt_util.utcnow()
            temp = self.coordinator.data.get(BOILER_TEMP_KEY)
            attributes = {"boiler_temperature": None if temp is None else temp.value}
            if self._on is not None and on != self._on:  # nothing fires for the first reading
                if on:
                    self._trigger_event("started", attributes)
                else:
                    if self._since is not None:
                        attributes["duration_seconds"] = round((now - self._since).total_seconds())
                    self._trigger_event("stopped", attributes)
            if on and (self._on is None or not self._on):
                self._since = now
            self._on = on
        super()._handle_coordinator_update()
