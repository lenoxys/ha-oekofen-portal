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
    data = entry.runtime_data
    entities: list[SensorEntity] = []
    for coordinator in (data.fast, data.slow):
        for key, reading in coordinator.data.items():
            if kind(reading) == "number" and key in data.docs.status:
                entities.append(OekofenStatusSensor(coordinator, key, data.names[key]))
            elif kind(reading) in ("number", "enum"):
                entities.append(OekofenSensor(coordinator, key, reading, data.names[key]))
    async_add_entities(entities)


class OekofenSensor(OekofenEntity, SensorEntity):
    """A sensor read from one portal variable."""

    def __init__(
        self, coordinator: OekofenCoordinator, key: str, reading: Reading, name: str
    ) -> None:
        super().__init__(coordinator, key)
        self._options: tuple[str, ...] | None = None
        if kind(reading) == "enum":
            # slugs for the mixing valve (translated), the portal's own labels otherwise;
            # fixed now so a later change of the portal language cannot break the entity
            self._options = MIXER_STATES if key == MIXER_KEY else reading.states
            self.entity_description = describe(
                key,
                SensorEntityDescription,
                name,
                device_class=SensorDeviceClass.ENUM,
                options=list(self._options),
            )
        else:
            device_class, unit = UNITS.get(reading.unit, (None, reading.unit or None))
            self.entity_description = describe(
                key,
                SensorEntityDescription,
                name,
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


class OekofenStatusSensor(OekofenEntity, SensorEntity):
    """A status word shown as ÖkoFEN's own text (each bit of the number is one message)."""

    def __init__(self, coordinator: OekofenCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key)
        self.entity_description = describe(key, SensorEntityDescription, name)

    @property
    def native_value(self) -> str | None:
        reading = self._reading
        if reading is None:
            return None
        raw = int(reading.value)
        return self.coordinator.config_entry.runtime_data.docs.decode(self._key, raw) or str(raw)

    @property
    def extra_state_attributes(self) -> dict[str, str | int]:
        reading = self._reading
        raw = {} if reading is None else {"raw": int(reading.value)}
        return {**self._attr_extra_state_attributes, **raw}
