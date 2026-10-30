"""Number entities: the writable temperature and curve settings of the allow-list."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OekofenConfigEntry
from .api import OekofenError
from .coordinator import OekofenCoordinator
from .entity import OekofenEntity, visible
from .settings import SETTINGS, Setting, check_number


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """One number per allow-listed setting the controller has."""
    coordinator = entry.runtime_data.slow
    async_add_entities(
        OekofenNumber(coordinator, setting)
        for setting in SETTINGS
        if setting.platform == "number"
        and setting.key in coordinator.data
        and visible(entry.runtime_data, setting.key)
    )


class OekofenNumber(OekofenEntity, NumberEntity):
    """A writable setting, bounded."""

    def __init__(self, coordinator: OekofenCoordinator, setting: Setting) -> None:
        super().__init__(coordinator, setting.key)
        self._setting = setting
        celsius = setting.unit == "°C"
        self.entity_description = NumberEntityDescription(
            key=setting.key,
            translation_key=setting.translation_key,
            native_min_value=setting.minimum,
            native_max_value=setting.maximum,
            native_step=setting.step,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS if celsius else setting.unit,
            device_class=NumberDeviceClass.TEMPERATURE if celsius else None,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
        )

    @property
    def native_value(self) -> float | None:
        reading = self._reading
        return None if reading is None else float(reading.value)

    async def async_set_native_value(self, value: float) -> None:
        reading = self._reading
        if reading is None:
            raise HomeAssistantError("The setting is not available")
        try:
            check_number(self._setting, value)
            await self.coordinator.client.async_write(
                self._key, round(value * reading.divisor)
            )
        except (ValueError, OekofenError) as err:
            raise HomeAssistantError(str(err)) from err
        # show the new value now; the next slow poll confirms it
        self.coordinator.async_set_updated_data(
            {**self.coordinator.data, self._key: reading._replace(value=value)}
        )
