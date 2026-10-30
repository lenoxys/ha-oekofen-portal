"""ÖkoFEN Portal: everything my.oekofen.info shows, as Home Assistant entities."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import OekofenPortalClient
from .catalog import load_catalog
from .const import DOMAIN, FAST_INTERVAL, FAST_VARIABLES, SLOW_INTERVAL
from .coordinator import OekofenCoordinator
from .docs import Docs, async_fetch_docs
from .entity import main_device_info
from .names import build_names
from .settings import SETTING_KEYS

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SENSOR]
DOCS_MAX_AGE = 7 * 24 * 3600


@dataclass
class OekofenData:
    """Two coordinators (a few variables often, the rest rarely) and the readable texts."""

    fast: OekofenCoordinator
    slow: OekofenCoordinator
    lang: str
    docs: Docs
    names: dict[str, str]


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


async def async_setup_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    session = async_get_clientsession(hass)
    client = OekofenPortalClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    catalog = await hass.async_add_executor_job(load_catalog)
    fast = OekofenCoordinator(hass, entry, client, FAST_VARIABLES, FAST_INTERVAL, "fast")
    # ponytail: reads the whole catalog every 5 min, restrict to enabled entities if the portal complains
    slow = OekofenCoordinator(
        hass,
        entry,
        client,
        [n for n in catalog if n not in FAST_VARIABLES] + SETTING_KEYS,
        SLOW_INTERVAL,
        "slow",
    )
    await fast.async_config_entry_first_refresh()
    await slow.async_config_entry_first_refresh()
    lang = "fr" if hass.config.language.startswith("fr") else "en"
    entry.runtime_data = OekofenData(
        fast,
        slow,
        lang,
        await _load_docs(hass, session, lang),
        build_names([*fast.data, *slow.data], lang),
    )
    # main device first, so the per-circuit devices can point at it
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **main_device_info(entry.entry_id, lang)
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
