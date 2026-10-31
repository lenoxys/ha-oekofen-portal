"""Switch entity: turns the solar boost on or off (off by default, kept across restarts)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import OekofenConfigEntry
from .entity import main_device_info

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SolarBoostSwitch(entry)])


class SolarBoostSwitch(SwitchEntity, RestoreEntity):
    """On: the integration raises the comfort (and opens the chosen radiator heads) when the sun allows it."""

    _attr_has_entity_name = True
    _attr_translation_key = "solar_boost"
    _attr_should_poll = False

    def __init__(self, entry: OekofenConfigEntry) -> None:
        self._boost = entry.runtime_data.boost
        self._attr_unique_id = f"{entry.entry_id}_solar_boost"
        self._attr_device_info = main_device_info(entry.entry_id, entry.runtime_data.texts)

    @property
    def is_on(self) -> bool:
        return self._boost.enabled

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state == "on":
            self._boost.enabled = True
            self.hass.async_create_task(self._boost.async_run())

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._boost.enabled = True
        await self._boost.async_run()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._boost.enabled = False
        await self._boost.async_run()
