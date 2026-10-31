"""Water heater entities: one per hot water circuit the controller has."""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_OFF,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .coordinator import OekofenCoordinator
from .entity import OekofenEntity, visible

PARALLEL_UPDATES = 1
STATE_AUTO = "auto"
OPERATION_BY_INDEX = {0: STATE_OFF, 1: STATE_AUTO, 2: STATE_PERFORMANCE}  # off, auto, forced on
INDEX_BY_OPERATION = {value: index for index, value in OPERATION_BY_INDEX.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """One water heater per hot water circuit that is present."""
    data = entry.runtime_data
    entities = []
    for n in range(3):
        key = f"LOCAL.ww[{n}].betriebsart[1]"
        if data.reading(key) is not None and visible(data, key):
            coordinator = data.fast if key in data.fast.data else data.slow
            entities.append(OekofenWaterHeater(coordinator, n))
    async_add_entities(entities)


class OekofenWaterHeater(OekofenEntity, WaterHeaterEntity):
    """A hot water circuit: top sensor of the tank, comfort target and operation mode."""

    _attr_name = None
    _attr_translation_key = "hot_water"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = [STATE_OFF, STATE_AUTO, STATE_PERFORMANCE]
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE
    )
    _attr_target_temperature_step = 1
    _attr_min_temp = 35
    _attr_max_temp = 70

    def __init__(self, coordinator: OekofenCoordinator, n: int) -> None:
        super().__init__(coordinator, f"LOCAL.ww[{n}].betriebsart[1]")
        self._n = n

    def _value(self, name: str):
        reading = self.data.reading(f"LOCAL.{name.format(n=self._n)}")
        return None if reading is None else reading.value

    @property
    def current_operation(self) -> str | None:
        value = self._value("ww[{n}].betriebsart[1]")
        return None if value is None else OPERATION_BY_INDEX.get(int(value))

    @property
    def current_temperature(self) -> float | None:
        return self._value("L_ww[{n}].einschaltfuehler_ist")

    @property
    def target_temperature(self) -> float | None:
        return self._value("ww[{n}].temp_heizen")  # the comfort setpoint

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            **self._attr_extra_state_attributes,
            "effective_target": self._value("L_ww[{n}].temp_soll"),
            "switch_off_sensor": self._value("L_ww[{n}].ausschaltfuehler_ist"),
            "pump": bool(self._value("L_ww[{n}].pumpe")),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (target := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self._async_set(f"LOCAL.ww[{self._n}].temp_heizen", target)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        await self._async_set(f"LOCAL.ww[{self._n}].betriebsart[1]", INDEX_BY_OPERATION[operation_mode])
