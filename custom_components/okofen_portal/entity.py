"""Base entity for the ÖkoFEN Portal integration."""

from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Reading
from .catalog import group_of, pretty
from .const import CURATED, DOMAIN
from .coordinator import OekofenCoordinator


def describe(key: str, description_cls: type[EntityDescription], **extra) -> EntityDescription:
    """Description for one variable: curated ones are named and enabled, the rest are diagnostics, disabled."""
    curated = CURATED.get(key)
    return description_cls(
        key=key,
        translation_key=curated[0] if curated else None,
        name=None if curated else pretty(key),
        entity_registry_enabled_default=curated[1] if curated else False,
        entity_category=None if curated else EntityCategory.DIAGNOSTIC,
        **extra,
    )


class OekofenEntity(CoordinatorEntity[OekofenCoordinator]):
    """An entity backed by one portal variable."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OekofenCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        group_id, group_name = group_of(key)
        if group_id == "system":
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry_id)}, manufacturer="ÖkoFEN", name="ÖkoFEN"
            )
        else:  # one device per circuit / function, under the main ÖkoFEN device
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry_id}_{group_id}")},
                manufacturer="ÖkoFEN",
                name=f"ÖkoFEN {group_name}",
                via_device=(DOMAIN, entry_id),
            )

    @property
    def _reading(self) -> Reading | None:
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        """Available when the last poll worked and returned this variable."""
        return super().available and self._reading is not None
