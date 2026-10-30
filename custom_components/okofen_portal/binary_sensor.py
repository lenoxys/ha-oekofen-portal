"""Binary sensors for the ÖkoFEN Portal integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .const import VAR_BURNER
from .entity import OekofenEntity

BURNER = BinarySensorEntityDescription(
    key=VAR_BURNER,
    translation_key="burner",
    device_class=BinarySensorDeviceClass.RUNNING,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the binary sensors."""
    async_add_entities([OekofenBinarySensor(entry.runtime_data, BURNER)])


class OekofenBinarySensor(OekofenEntity, BinarySensorEntity):
    """The burner contact of the existing boiler."""

    def __init__(self, coordinator, description: BinarySensorEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.get(self._key)
        return None if value is None else bool(value)
