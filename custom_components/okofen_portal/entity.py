"""Base entity for the ÖkoFEN Portal integration."""

from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import OekofenError, Reading
from .catalog import group_of
from .const import COVERED_BY_WEATHER, CURATED, DASHBOARD, DOMAIN, FORECAST_DAY_KEY
from .control import prepare
from .coordinator import OekofenCoordinator
from .names import Texts

PANEL_KEYS = set(DASHBOARD.values())


def describe(
    key: str, description_cls: type[EntityDescription], name: str | None, **extra
) -> EntityDescription:
    """Description for one variable: curated ones are named and enabled, the rest are diagnostics, disabled.

    The values the panel draws are enabled too: the recorder keeps their history, which the panel replays.
    """
    curated = CURATED.get(key) or (("forecast_day", True) if key == FORECAST_DAY_KEY else None)
    return description_cls(
        key=key,
        translation_key=curated[0] if curated else None,
        name=None if curated else name,
        entity_registry_enabled_default=curated[1] if curated else key in PANEL_KEYS,
        entity_category=None if curated else EntityCategory.DIAGNOSTIC,
        **extra,
    )


def visible(data, key: str) -> bool:
    """False for variables of equipment the controller does not have, or already shown elsewhere."""
    return group_of(key) not in data.hidden and key not in COVERED_BY_WEATHER


def main_device_info(entry_id: str, texts: Texts) -> DeviceInfo:
    """The main ÖkoFEN device, home of the controller's general values."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        manufacturer="ÖkoFEN",
        name="ÖkoFEN",
        model=texts.group_description("system"),
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
        group_id = group_of(key)
        if group_id == "system":
            self._attr_device_info = main_device_info(entry_id, data.texts)
        else:  # one device per circuit / function, under the main ÖkoFEN device
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry_id}_{group_id}")},
                manufacturer="ÖkoFEN",
                name=f"ÖkoFEN {data.texts.group_title(group_id)}",
                model=data.texts.group_description(group_id),
                via_device_id=data.main_device_id,
            )
        # ÖkoFEN's own help text when the portal has one, otherwise our explanation
        self._attr_extra_state_attributes = {
            "description": data.docs.help.get(key) or data.texts.entity_description(key),
            "portal_variable": key,
        }

    @property
    def _reading(self) -> Reading | None:
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        """Available when the last poll worked and returned this variable."""
        return super().available and self._reading is not None

    @property
    def data(self):
        """Everything the integration holds (both coordinators, names, docs)."""
        return self.coordinator.config_entry.runtime_data

    async def async_added_to_hass(self) -> None:
        """Also follow the other coordinator: climate and water heater mix fast and slow values."""
        await super().async_added_to_hass()
        for other in (self.data.fast, self.data.slow):
            if other is not self.coordinator:
                self.async_on_remove(other.async_add_listener(self._handle_coordinator_update))

    async def _async_set(self, key: str, value: float) -> None:
        """Write one allow-listed setting (bounds checked) and show it at once."""
        reading = self.data.reading(key)
        if reading is None:
            raise HomeAssistantError(f"{key} is not available")
        try:
            raw, shown = prepare(key, value, reading)
            await self.coordinator.client.async_write(key, raw)
        except (ValueError, OekofenError) as err:
            raise HomeAssistantError(str(err)) from err
        self.data.update(key, reading._replace(value=shown))
