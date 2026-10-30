"""Data update coordinator for the ÖkoFEN Portal integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OekofenAuthError,
    OekofenConnectionError,
    OekofenPortalClient,
)
from .const import DOMAIN, SCAN_INTERVAL, VARIABLES

_LOGGER = logging.getLogger(__name__)


class OekofenCoordinator(DataUpdateCoordinator[dict[str, float | int | str]]):
    """Poll the portal for the variables used by the entities."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: OekofenPortalClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, float | int | str]:
        try:
            return await self.client.async_read(VARIABLES)
        except OekofenAuthError as err:
            raise ConfigEntryAuthFailed from err
        except OekofenConnectionError as err:
            raise UpdateFailed(f"Portal unreachable: {err}") from err
