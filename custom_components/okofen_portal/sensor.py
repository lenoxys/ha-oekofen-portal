"""Sensors for the ÖkoFEN Portal integration: numbers and multi-state variables."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .api import Reading
from .catalog import kind
from .const import MIXER_KEY, MIXER_STATES
from .coordinator import OekofenCoordinator
from .entity import OekofenEntity, describe

# portal unit text -> (device class, Home Assistant unit); anything else keeps its own unit
UNITS: dict[str, tuple[SensorDeviceClass, str]] = {
    "°C": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    "W": (SensorDeviceClass.POWER, UnitOfPower.WATT),
    "kW": (SensorDeviceClass.POWER, UnitOfPower.KILO_WATT),
    "kWh": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR),
    "V": (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT),
    "A": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE),
    "sec": (SensorDeviceClass.DURATION, UnitOfTime.SECONDS),
    "min": (SensorDeviceClass.DURATION, UnitOfTime.MINUTES),
    "h": (SensorDeviceClass.DURATION, UnitOfTime.HOURS),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create one sensor per numeric or multi-state variable the controller returned."""
    entities: list[OekofenSensor] = []
    for coordinator in (entry.runtime_data.fast, entry.runtime_data.slow):
        for key, reading in coordinator.data.items():
            if kind(reading) in ("number", "enum"):
                entities.append(OekofenSensor(coordinator, key, reading))
    async_add_entities(entities)


class OekofenSensor(OekofenEntity, SensorEntity):
    """A sensor read from one portal variable."""

    def __init__(self, coordinator: OekofenCoordinator, key: str, reading: Reading) -> None:
        super().__init__(coordinator, key)
        self._options: tuple[str, ...] | None = None
        if kind(reading) == "enum":
            # slugs for the mixing valve (translated), the portal's own labels otherwise;
            # fixed now so a later change of the portal language cannot break the entity
            self._options = MIXER_STATES if key == MIXER_KEY else reading.states
            self.entity_description = describe(
                key,
                SensorEntityDescription,
                device_class=SensorDeviceClass.ENUM,
                options=list(self._options),
            )
        else:
            device_class, unit = UNITS.get(reading.unit, (None, reading.unit or None))
            self.entity_description = describe(
                key,
                SensorEntityDescription,
                device_class=device_class,
                native_unit_of_measurement=unit,
                state_class=(
                    SensorStateClass.TOTAL_INCREASING
                    if device_class == SensorDeviceClass.ENERGY
                    else SensorStateClass.MEASUREMENT
                ),
            )

    @property
    def native_value(self):
        reading = self._reading
        if reading is None:
            return None
        if self._options is not None:
            index = int(reading.value)
            return self._options[index] if 0 <= index < len(self._options) else None
        return reading.value
