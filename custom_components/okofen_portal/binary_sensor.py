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
from .const import BURNER_KEY, FORECAST_DAY_KEY
from .entity import OekofenEntity, describe, visible
from .settings import SETTING_KEYS

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create one binary sensor per two-state variable the controller returned."""
    data = entry.runtime_data
    async_add_entities(
        OekofenBinarySensor(coordinator, key, data.names[key])
        for coordinator in (data.fast, data.slow)
        for key, reading in coordinator.data.items()
        if kind(reading) == "binary"
        and key != FORECAST_DAY_KEY
        and key not in SETTING_KEYS
        and visible(data, key)
    )
    async_add_entities(
        OekofenPumpRunning(coordinator, key)
        for coordinator in (data.fast, data.slow)
        for key, reading in coordinator.data.items()
        if key.endswith(".pumpe") and reading.unit == "%" and visible(data, key)
    )


class OekofenBinarySensor(OekofenEntity, BinarySensorEntity):
    """A two-state variable, on when its value is 1."""

    def __init__(self, coordinator: OekofenCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key)
        self.entity_description = describe(
            key,
            BinarySensorEntityDescription,
            name,
            device_class=BinarySensorDeviceClass.RUNNING if key == BURNER_KEY else None,
        )

    @property
    def is_on(self) -> bool | None:
        reading = self._reading
        return None if reading is None else bool(reading.value)


class OekofenPumpRunning(OekofenEntity, BinarySensorEntity):
    """On when a pump with a speed in % is running (the speed itself is a sensor)."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "pump_running"

    def __init__(self, coordinator: OekofenCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._attr_unique_id = f"{self._attr_unique_id}_running"

    @property
    def is_on(self) -> bool | None:
        reading = self._reading
        return None if reading is None else float(reading.value) > 0
