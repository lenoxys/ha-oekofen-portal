"""Scene entities: presets that set several settings at once."""

from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .api import OekofenError
from .const import DOMAIN
from .control import async_apply
from .entity import main_device_info
from .presets import PRESETS

PARALLEL_UPDATES = 1


PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """The built-in presets, when the controller has the settings they change."""
    data = entry.runtime_data
    async_add_entities(
        OekofenScene(entry, name)
        for name, plan in PRESETS.items()
        if any(data.reading(key) is not None for key in plan)
    )


class OekofenScene(Scene):
    """Writes a set of settings; if one write fails, the earlier ones are put back."""

    _attr_has_entity_name = True

    def __init__(self, entry: OekofenConfigEntry, name: str) -> None:
        self._entry = entry
        self._name = name
        self._attr_translation_key = name
        self._attr_unique_id = f"{entry.entry_id}_scene_{name}"
        self._attr_device_info = main_device_info(entry.entry_id, entry.runtime_data.texts)

    async def async_activate(self, **kwargs: Any) -> None:
        data = self._entry.runtime_data
        plan = PRESETS[self._name]
        readings = {key: data.reading(key) for key in plan if data.reading(key) is not None}
        try:
            changed = await async_apply(data.fast.client, readings, plan)
        except (ValueError, OekofenError) as err:
            raise HomeAssistantError(f"Scene {self._name} not applied: {err}") from err
        for key in readings:
            data.update(key, changed[key])
