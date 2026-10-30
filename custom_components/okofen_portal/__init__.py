"""ÖkoFEN Portal: everything my.oekofen.info shows, as Home Assistant entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OekofenPortalClient
from .catalog import load_catalog
from .const import FAST_INTERVAL, FAST_VARIABLES, SLOW_INTERVAL
from .coordinator import OekofenCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


@dataclass
class OekofenData:
    """The two coordinators: a few variables often, the rest of the catalog rarely."""

    fast: OekofenCoordinator
    slow: OekofenCoordinator


type OekofenConfigEntry = ConfigEntry[OekofenData]


async def async_setup_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    client = OekofenPortalClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    catalog = await hass.async_add_executor_job(load_catalog)
    fast = OekofenCoordinator(hass, entry, client, FAST_VARIABLES, FAST_INTERVAL, "fast")
    # ponytail: reads the whole catalog every 5 min, restrict to enabled entities if the portal complains
    slow = OekofenCoordinator(
        hass,
        entry,
        client,
        [n for n in catalog if n not in FAST_VARIABLES],
        SLOW_INTERVAL,
        "slow",
    )
    await fast.async_config_entry_first_refresh()
    await slow.async_config_entry_first_refresh()
    entry.runtime_data = OekofenData(fast, slow)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
