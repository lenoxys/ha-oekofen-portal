"""Data update coordinators for the ÖkoFEN Portal integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
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
        self.portal_error: str | None = None  # why the portal did not answer, None while it does
        self._portal_failures = 0
        self._repairs = label == "fast"  # one coordinator raises the repair, the slow one fails now and then on its own
        self._issue = f"portal_unreachable_{entry.entry_id}"

    async def _async_update_data(self) -> dict[str, Reading]:
        """Read, and space out the next tries while the portal does not answer."""
        try:
            data = await self._read()
        except UpdateFailed:
            delay = RETRY_DELAYS[self._failures] if self._failures < len(RETRY_DELAYS) else RETRY_MAX
            self._failures += 1
            self.update_interval = timedelta(seconds=delay)
            self._report(local=False)
            raise
        self._failures = 0
        self.update_interval = self._interval
        self._report(local=True)
        return data

    def _portal(self, err: Exception | None) -> None:
        self.portal_error = None if err is None else str(err)
        self._portal_failures = 0 if err is None else self._portal_failures + 1

    def _report(self, local: bool) -> None:
        """Setting up (no data yet) or 3 portal failures in a row: tell the user in Repairs, until it answers."""
        if not self._repairs:
            return
        if self.portal_error is None:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue)
        elif self.data is None or self._portal_failures >= 3:
            ir.async_create_issue(
                self.hass, DOMAIN, self._issue, is_fixable=False,
                severity=ir.IssueSeverity.WARNING if local else ir.IssueSeverity.ERROR,
                translation_key="portal_unreachable_local" if local else "portal_unreachable",
                translation_placeholders={"error": self.portal_error},
            )

    async def _read(self, names: list[str] | None = None) -> dict[str, Reading]:
        try:
            data = await self.client.async_read(self.names if names is None else names)
        except OekofenAuthError as err:
            raise ConfigEntryAuthFailed from err
        except OekofenConnectionError as err:
            self._portal(err)
            raise UpdateFailed(f"Portal unreachable: {err}") from err
        self._portal(None)
        return data


class HybridCoordinator(OekofenCoordinator):
    """The fast variables: the local interface often, the portal for what only it knows.

    If the local interface does not answer, the whole list is read from the portal for that cycle.
    If the portal does not answer, the local values go on alone (the portal ones go after 3 tries).
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
                self._cloud = await super()._read(self._cloud_names)
            except UpdateFailed as err:
                if self._portal_failures >= 3:  # a blip keeps the last values, an outage does not
                    self._cloud = {}
                _LOGGER.debug("Local values only: %s", err)
            self._cloud_at = now  # next try of the portal in cloud_interval, answer or not
        return {**self._cloud, **local}
