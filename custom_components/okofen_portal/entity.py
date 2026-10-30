"""Base entity for the ÖkoFEN Portal integration."""

from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Reading
from .catalog import group_of
from .const import COVERED_BY_WEATHER, CURATED, DOMAIN, TRANSLATED
from .coordinator import OekofenCoordinator
from .names import entity_description, group_description, group_title


def describe(
    key: str, description_cls: type[EntityDescription], name: str | None, **extra
) -> EntityDescription:
    """Description for one variable: curated ones are named and enabled, the rest are diagnostics, disabled."""
    curated = CURATED.get(key) or ((TRANSLATED[key], True) if key in TRANSLATED else None)
    return description_cls(
        key=key,
        translation_key=curated[0] if curated else None,
        name=None if curated else name,
        entity_registry_enabled_default=curated[1] if curated else False,
        entity_category=None if curated else EntityCategory.DIAGNOSTIC,
        **extra,
    )


def visible(data, key: str) -> bool:
    """False for variables of equipment the controller does not have, or already shown elsewhere."""
    return group_of(key)[0] not in data.hidden and key not in COVERED_BY_WEATHER


def main_device_info(entry_id: str, lang: str) -> DeviceInfo:
    """The main ÖkoFEN device, home of the controller's general values."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        manufacturer="ÖkoFEN",
        name="ÖkoFEN",
        model=group_description("system", lang),
    )


class OekofenEntity(CoordinatorEntity[OekofenCoordinator]):
    """An entity backed by one portal variable."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OekofenCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        data = coordinator.config_entry.runtime_data
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        group_id, _ = group_of(key)
        if group_id == "system":
            self._attr_device_info = main_device_info(entry_id, data.lang)
        else:  # one device per circuit / function, under the main ÖkoFEN device
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry_id}_{group_id}")},
                manufacturer="ÖkoFEN",
                name=f"ÖkoFEN {group_title(group_id, data.lang)}",
                model=group_description(group_id, data.lang),
                via_device=(DOMAIN, entry_id),
            )
        # ÖkoFEN's own help text when the portal has one, otherwise our explanation
        self._attr_extra_state_attributes = {
            "description": data.docs.help.get(key) or entity_description(key, data.lang),
            "portal_variable": key,
        }

    @property
    def _reading(self) -> Reading | None:
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        """Available when the last poll worked and returned this variable."""
        return super().available and self._reading is not None
