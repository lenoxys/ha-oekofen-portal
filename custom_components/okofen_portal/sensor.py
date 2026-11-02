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
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_time_change

from . import OekofenConfigEntry
from .api import Reading
from .boost import STATES as BOOST_STATES
from .catalog import kind
from .const import CLOCK_KEYS, FORECAST_DAY_KEY, FORECAST_DAY_STATES, MIXER_KEY, MIXER_STATES
from .coordinator import OekofenCoordinator
from .entity import OekofenEntity, describe, main_device_info, visible
from .history import async_learning
from .settings import SETTING_KEYS

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


PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create one sensor per numeric or multi-state variable the controller returned."""
    data = entry.runtime_data
    entities: list[SensorEntity] = [SolarBoostSensor(entry), LearningSensor(entry)]
    for coordinator in (data.fast, data.slow):
        for key, reading in coordinator.data.items():
            if not visible(data, key) or kind(reading) == "text" or key in SETTING_KEYS:
                continue
            if key in CLOCK_KEYS:
                entities.append(OekofenClockSensor(coordinator, key, data.names[key]))
            elif kind(reading) == "number" and key in data.docs.status:
                entities.append(OekofenStatusSensor(coordinator, key, data.names[key]))
            elif kind(reading) in ("number", "enum") or key == FORECAST_DAY_KEY:
                entities.append(OekofenSensor(coordinator, key, reading, data.names[key]))
    async_add_entities(entities)


class OekofenSensor(OekofenEntity, SensorEntity):
    """A sensor read from one portal variable."""

    def __init__(
        self, coordinator: OekofenCoordinator, key: str, reading: Reading, name: str
    ) -> None:
        super().__init__(coordinator, key)
        self._options: tuple[str, ...] | None = None
        if kind(reading) == "enum" or key == FORECAST_DAY_KEY:
            # slugs for the mixing valve and the forecast day (translated), the portal's own labels
            # otherwise; fixed now so a later change of the portal language cannot break the entity
            self._options = (
                MIXER_STATES
                if key == MIXER_KEY
                else FORECAST_DAY_STATES if key == FORECAST_DAY_KEY else reading.states
            )
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


class _TextSensor(OekofenEntity, SensorEntity):
    """A number shown as text: no unit, no device class."""

    def __init__(self, coordinator: OekofenCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key)
        self.entity_description = describe(key, SensorEntityDescription, name)


class OekofenStatusSensor(_TextSensor):
    """A status word shown as ÖkoFEN's own text (each bit of the number is one message)."""

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


class OekofenClockSensor(_TextSensor):
    """A time of day that the controller stores as a number (1750 = 17:50)."""

    @property
    def native_value(self) -> str | None:
        reading = self._reading
        if reading is None:
            return None
        hhmm = int(reading.value)
        return f"{hhmm // 100:02d}:{hhmm % 100:02d}"


class SolarBoostSensor(SensorEntity):
    """What the solar boost is doing, and why (``reason`` attribute): to follow it without the logs."""

    _attr_has_entity_name = True
    _attr_translation_key = "solar_boost_state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(BOOST_STATES)
    _attr_should_poll = False

    def __init__(self, entry: OekofenConfigEntry) -> None:
        self._boost = entry.runtime_data.boost
        self._attr_unique_id = f"{entry.entry_id}_solar_boost_state"
        self._attr_device_info = main_device_info(entry.entry_id, entry.runtime_data.texts)

    @property
    def native_value(self) -> str:
        return self._boost.state

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"reason": self._boost.reason}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, self._boost.signal, self.async_write_ha_state))


class LearningSensor(SensorEntity):
    """The house's inertia learnt from the recorder (learning.py): *learning* with its progress, then *ready* with the values."""

    _attr_has_entity_name = True
    _attr_translation_key = "heating_learning"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["learning", "ready"]
    _attr_should_poll = False

    def __init__(self, entry: OekofenConfigEntry) -> None:
        self._data = entry.runtime_data
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_heating_learning"
        self._attr_device_info = main_device_info(entry.entry_id, entry.runtime_data.texts)

    @property
    def native_value(self) -> str | None:
        return self._data.learning and self._data.learning["state"]

    @property
    def extra_state_attributes(self) -> dict:
        return {k: v for k, v in (self._data.learning or {}).items() if k != "state"}

    async def _update(self, _now=None) -> None:
        self._data.learning = await async_learning(self.hass, self._entry_id)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        # once at start (the recorder may still be loading: a few minutes later), then every night
        self.async_on_remove(async_call_later(self.hass, 120, self._update))
        self.async_on_remove(async_track_time_change(self.hass, self._update, hour=4, minute=10, second=0))
