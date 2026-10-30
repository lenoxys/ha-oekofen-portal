"""Binary sensors for the ÖkoFEN Portal integration: two-state variables."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .catalog import kind
from .coordinator import OekofenCoordinator
from .entity import OekofenEntity, describe

BURNER_KEY = "LOCAL.L_ke_brennerkontakt_1"


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create one binary sensor per two-state variable the controller returned."""
    async_add_entities(
        OekofenBinarySensor(coordinator, key)
        for coordinator in (entry.runtime_data.fast, entry.runtime_data.slow)
        for key, reading in coordinator.data.items()
        if kind(reading) == "binary"
    )


class OekofenBinarySensor(OekofenEntity, BinarySensorEntity):
    """A two-state variable, on when its value is 1."""

    def __init__(self, coordinator: OekofenCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self.entity_description = describe(
            key,
            BinarySensorEntityDescription,
            device_class=BinarySensorDeviceClass.RUNNING if key == BURNER_KEY else None,
        )

    @property
    def is_on(self) -> bool | None:
        reading = self._reading
        return None if reading is None else bool(reading.value)
