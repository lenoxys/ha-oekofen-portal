"""Data update coordinators for the ÖkoFEN Portal integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OekofenAuthError,
    OekofenConnectionError,
    OekofenPortalClient,
    Reading,
)
from .const import DOMAIN, RETRY_DELAYS, RETRY_MAX
from .local import MAP, OekofenLocalClient

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
        self._interval = interval
        self._failures = 0

    async def _async_update_data(self) -> dict[str, Reading]:
        """Read, and space out the next tries while the portal does not answer."""
        try:
            data = await self._read()
        except UpdateFailed:
            delay = RETRY_DELAYS[self._failures] if self._failures < len(RETRY_DELAYS) else RETRY_MAX
            self._failures += 1
            self.update_interval = timedelta(seconds=delay)
            raise
        self._failures = 0
        self.update_interval = self._interval
        return data

    async def _read(self) -> dict[str, Reading]:
        try:
            return await self.client.async_read(self.names)
        except OekofenAuthError as err:
            raise ConfigEntryAuthFailed from err
        except OekofenConnectionError as err:
            raise UpdateFailed(f"Portal unreachable: {err}") from err


class HybridCoordinator(OekofenCoordinator):
    """The fast variables: the local interface often, the portal for what only it knows.

    If the local interface does not answer, the whole list is read from the portal for that cycle.
    """

    def __init__(self, *args, local: OekofenLocalClient, cloud_interval: timedelta, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._local = local
        self._cloud_interval = cloud_interval
        self._cloud_names = [n for n in self.names if n not in MAP]
        self._cloud: dict[str, Reading] = {}
        self._cloud_at: datetime | None = None

    async def _read(self) -> dict[str, Reading]:
        now = dt_util.utcnow()
        try:
            local = await self._local.async_read()
        except OekofenConnectionError as err:
            _LOGGER.debug("Local interface unavailable, using the portal: %s", err)
            self._cloud_at = None
            return await super()._read()
        if self._cloud_at is None or now - self._cloud_at >= self._cloud_interval:
            try:
                self._cloud = await self.client.async_read(self._cloud_names)
            except OekofenAuthError as err:
                raise ConfigEntryAuthFailed from err
            except OekofenConnectionError as err:
                if not self._cloud:  # otherwise keep the last portal values until it answers again
                    raise UpdateFailed(f"Portal unreachable: {err}") from err
                _LOGGER.debug("Portal unreachable, keeping the last values: %s", err)
            else:
                self._cloud_at = now
        return {**self._cloud, **local}
