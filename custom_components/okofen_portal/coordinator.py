"""Data update coordinators for the ÖkoFEN Portal integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OekofenAuthError,
    OekofenConnectionError,
    OekofenPortalClient,
    Reading,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OekofenCoordinator(DataUpdateCoordinator[dict[str, Reading]]):
    """Poll a fixed list of portal variables."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: OekofenPortalClient,
        names: list[str],
        interval: timedelta,
        label: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {label}",
            update_interval=interval,
            always_update=False,
        )
        self.client = client
        self.names = names

    async def _async_update_data(self) -> dict[str, Reading]:
        try:
            return await self.client.async_read(self.names)
        except OekofenAuthError as err:
            raise ConfigEntryAuthFailed from err
        except OekofenConnectionError as err:
            raise UpdateFailed(f"Portal unreachable: {err}") from err
