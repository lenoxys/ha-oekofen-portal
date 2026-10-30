"""ÖkoFEN Portal: everything my.oekofen.info shows, as Home Assistant entities."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import OekofenPortalClient
from .local import OekofenLocalClient
from .catalog import group_of, kind, load_catalog
from .const import (
    CONF_LOCAL_HOST,
    CONF_LOCAL_PASSWORD,
    DOMAIN,
    FAST_INTERVAL,
    FAST_VARIABLES,
    LOCAL_INTERVAL,
    SLOW_INTERVAL,
)
from .dashboard import async_setup_dashboard
from .coordinator import HybridCoordinator, OekofenCoordinator
from .docs import Docs, async_fetch_docs
from .entity import main_device_info
from .names import Texts
from .presence import FLAG_KEYS, hidden_groups
from .settings import SETTING_KEYS
from .weather_parse import WEATHER_KEYS

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SCENE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.WATER_HEATER,
    Platform.WEATHER,
]
DOCS_MAX_AGE = 7 * 24 * 3600
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class OekofenData:
    """Two coordinators (a few variables often, the rest rarely) and the readable texts."""

    fast: OekofenCoordinator
    slow: OekofenCoordinator
    texts: Texts
    docs: Docs
    names: dict[str, str]
    hidden: set[str]

    def reading(self, key: str):
        """A variable from whichever coordinator reads it."""
        return self.fast.data.get(key) or self.slow.data.get(key)

    def update(self, key: str, reading) -> None:
        """Show a value we just wrote right away (the next poll confirms it)."""
        for coordinator in (self.fast, self.slow):
            if key in coordinator.data:
                coordinator.async_set_updated_data({**coordinator.data, key: reading})


type OekofenConfigEntry = ConfigEntry[OekofenData]


async def _load_docs(hass: HomeAssistant, session: aiohttp.ClientSession, lang: str) -> Docs:
    """ÖkoFEN's labels and help texts: cached for a week, empty if the portal does not answer."""
    store: Store = Store(hass, 1, f"{DOMAIN}_docs_{lang}")
    cached = await store.async_load()
    if cached and time.time() - cached.get("time", 0) < DOCS_MAX_AGE:
        return Docs.from_dict(cached["docs"])
    try:
        docs = await async_fetch_docs(session, lang, set(SETTING_KEYS))
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return Docs.from_dict(cached["docs"]) if cached else Docs()
    await store.async_save({"time": time.time(), "docs": docs.to_dict()})
    return docs


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the sidebar panel once."""
    await async_setup_dashboard(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    session = async_get_clientsession(hass)
    client = OekofenPortalClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    catalog = await hass.async_add_executor_job(load_catalog)
    if entry.data.get(CONF_LOCAL_HOST):  # optional: local interface for the fast variables
        fast = HybridCoordinator(
            hass, entry, client, FAST_VARIABLES, LOCAL_INTERVAL, "fast",
            local=OekofenLocalClient(session, entry.data[CONF_LOCAL_HOST], entry.data.get(CONF_LOCAL_PASSWORD, "")),
            cloud_interval=FAST_INTERVAL,
        )
    else:
        fast = OekofenCoordinator(hass, entry, client, FAST_VARIABLES, FAST_INTERVAL, "fast")
    # ponytail: reads the whole catalog every 5 min, restrict to enabled entities if the portal complains
    slow = OekofenCoordinator(
        hass,
        entry,
        client,
        [n for n in [*catalog, *SETTING_KEYS, *WEATHER_KEYS] if n not in FAST_VARIABLES],
        SLOW_INTERVAL,
        "slow",
    )
    await fast.async_config_entry_first_refresh()
    await slow.async_config_entry_first_refresh()
    texts = await hass.async_add_executor_job(Texts.load, hass.config.language)
    readings = {k: r for k, r in {**fast.data, **slow.data}.items() if kind(r) != "text"}
    # the portal answers for circuits the controller does not have: leave those out
    hidden = hidden_groups(await client.async_read(FLAG_KEYS), readings)
    shown = [k for k in readings if group_of(k) not in hidden]
    entry.runtime_data = OekofenData(
        fast,
        slow,
        texts,
        await _load_docs(hass, session, texts.lang),
        texts.build_names(shown),
        hidden,
    )
    registry = dr.async_get(hass)
    # main device first, so the per-circuit devices can point at it
    registry.async_get_or_create(
        config_entry_id=entry.entry_id, **main_device_info(entry.entry_id, texts)
    )
    # devices created by earlier versions for equipment that is not there
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        ids = {identifier for domain, identifier in device.identifiers if domain == DOMAIN}
        if any(f"{entry.entry_id}_{group}" in ids for group in hidden):
            registry.async_remove_device(device.id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
