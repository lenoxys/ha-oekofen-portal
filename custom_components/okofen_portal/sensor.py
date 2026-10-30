"""Sensors for the ÖkoFEN Portal integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .const import (
    MIXER_STATES,
    VAR_BOILER_SETPOINT,
    VAR_BOILER_TEMP,
    VAR_MIXER,
)
from .entity import OekofenEntity

DESCRIPTIONS = (
    SensorEntityDescription(
        key=VAR_BOILER_TEMP,
        translation_key="boiler_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key=VAR_BOILER_SETPOINT,
        translation_key="boiler_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=VAR_MIXER,
        translation_key="heating_mixer",
        device_class=SensorDeviceClass.ENUM,
        options=list(MIXER_STATES.values()),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    async_add_entities(
        OekofenSensor(entry.runtime_data, description) for description in DESCRIPTIONS
    )


class OekofenSensor(OekofenEntity, SensorEntity):
    """A sensor read from one portal variable."""

    def __init__(self, coordinator, description: SensorEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._key)
        if self._key == VAR_MIXER:
            return MIXER_STATES.get(int(value)) if value is not None else None
        return value
