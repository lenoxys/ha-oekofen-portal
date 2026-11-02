"""Climate entities: one thermostat per heating circuit the controller has."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    PRESET_COMFORT,
    PRESET_ECO,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .coordinator import OekofenCoordinator
from .entity import OekofenEntity, visible

PARALLEL_UPDATES = 1
# portal value of betriebsart[1] <-> Home Assistant
HVAC_BY_INDEX = {0: HVACMode.OFF, 1: HVACMode.AUTO, 2: HVACMode.HEAT, 3: HVACMode.HEAT}
PRESET_BY_INDEX = {2: PRESET_COMFORT, 3: PRESET_ECO}  # comfort, and setback ("reduced")
INDEX_BY_HVAC = {HVACMode.OFF: 0, HVACMode.AUTO: 1, HVACMode.HEAT: 2}  # HEAT is ambiguous: comfort
INDEX_BY_PRESET = {preset: index for index, preset in PRESET_BY_INDEX.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """One thermostat per heating circuit that is present."""
    data = entry.runtime_data
    entities = []
    for n in range(6):
        key = f"LOCAL.hk[{n}].betriebsart[1]"
        if data.reading(key) is not None and visible(data, key):
            coordinator = data.fast if key in data.fast.data else data.slow
            entities.append(OekofenClimate(coordinator, n))
    async_add_entities(entities)


class OekofenClimate(OekofenEntity, ClimateEntity):
    """A heating circuit: room temperature, comfort target, mode and what the pump is doing."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT]
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 10
    _attr_max_temp = 30

    def __init__(self, coordinator: OekofenCoordinator, n: int) -> None:
        super().__init__(coordinator, f"LOCAL.hk[{n}].betriebsart[1]")
        self._n = n

    @property
    def _index(self) -> int | None:
        value = self._value("hk[{n}].betriebsart[1]")
        return None if value is None else int(value)

    @property
    def hvac_mode(self) -> HVACMode | None:
        return HVAC_BY_INDEX.get(self._index)

    @property
    def preset_mode(self) -> str | None:
        return PRESET_BY_INDEX.get(self._index)

    @property
    def hvac_action(self) -> HVACAction | None:
        if self._index == 0:
            return HVACAction.OFF
        return HVACAction.HEATING if self._value("L_hk[{n}].pumpe") else HVACAction.IDLE

    @property
    def current_temperature(self) -> float | None:
        return self._value("L_hk[{n}].raumtemp_ist")

    @property
    def target_temperature(self) -> float | None:
        return self._value("hk[{n}].raumtemp_heizen")  # the comfort setpoint

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self.data.docs.decode(f"LOCAL.L_hk[{self._n}].status", int(self._value("L_hk[{n}].status") or 0))
        return {
            **self._attr_extra_state_attributes,
            "effective_target": self._value("L_hk[{n}].raumtemp_soll"),
            "flow_temperature": self._value("L_hk[{n}].vorlauftemp_ist"),
            "flow_setpoint": self._value("L_hk[{n}].vorlauftemp_soll"),
            "status": status,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (target := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self._async_set(f"LOCAL.hk[{self._n}].raumtemp_heizen", target)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._async_set(f"LOCAL.hk[{self._n}].betriebsart[1]", INDEX_BY_HVAC[hvac_mode])

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._async_set(f"LOCAL.hk[{self._n}].betriebsart[1]", INDEX_BY_PRESET[preset_mode])

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)
