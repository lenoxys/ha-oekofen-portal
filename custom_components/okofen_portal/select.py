"""Select entities: the writable multi-state settings of the allow-list."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .coordinator import OekofenCoordinator
from .entity import OekofenEntity, visible
from .settings import SETTINGS, Setting


PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """One select per allow-listed setting the controller has."""
    coordinator = entry.runtime_data.slow
    async_add_entities(
        OekofenSelect(coordinator, setting)
        for setting in SETTINGS
        if setting.platform == "select"
        and setting.key in coordinator.data
        and visible(entry.runtime_data, setting.key)
    )


class OekofenSelect(OekofenEntity, SelectEntity):
    """A writable setting limited to the options of the allow-list."""

    def __init__(self, coordinator: OekofenCoordinator, setting: Setting) -> None:
        super().__init__(coordinator, setting.key)
        self._setting = setting
        self._index_of = {slug: index for index, slug in setting.options.items()}
        self.entity_description = SelectEntityDescription(
            key=setting.key,
            translation_key=setting.translation_key,
            options=list(setting.options.values()),
            entity_category=EntityCategory.CONFIG,
        )

    @property
    def current_option(self) -> str | None:
        reading = self._reading
        return None if reading is None else self._setting.options.get(int(reading.value))

    async def async_select_option(self, option: str) -> None:
        await self._async_set(self._key, self._index_of[option])
