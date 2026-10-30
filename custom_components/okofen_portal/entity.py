"""Base entity for the ÖkoFEN Portal integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OekofenCoordinator


class OekofenEntity(CoordinatorEntity[OekofenCoordinator]):
    """An entity backed by one portal variable."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OekofenCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer="ÖkoFEN",
            name="ÖkoFEN",
        )

    @property
    def available(self) -> bool:
        """Available when the last poll worked and returned this variable."""
        return super().available and self._key in self.coordinator.data
