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
from homeassistant.helpers import config_validation as cv, device_registry as dr, issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import OekofenConnectionError, OekofenPortalClient, Reading
from .boost import SolarBoost
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
from .solar_boost import KEYS as BOOST_KEYS
from .weather_parse import WEATHER_KEYS

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SCENE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
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
    boost: SolarBoost | None = None
    main_device_id: str = ""  # registry id of the main ÖkoFEN device, parent of the per-circuit devices

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
    local = entry.data.get(CONF_LOCAL_HOST)
    if local:  # optional: local interface for the fast variables and the settings it has
        client.local = OekofenLocalClient(session, local, entry.data.get(CONF_LOCAL_PASSWORD, ""))
        fast = HybridCoordinator(
            hass, entry, client, FAST_VARIABLES, LOCAL_INTERVAL, "fast", local=client.local, cloud_interval=FAST_INTERVAL
        )
    else:
        fast = OekofenCoordinator(hass, entry, client, FAST_VARIABLES, FAST_INTERVAL, "fast")
    # ponytail: reads the whole catalog every 5 min, restrict to enabled entities if the portal complains
    slow = OekofenCoordinator(
        hass,
        entry,
        client,
        [n for n in dict.fromkeys([*catalog, *SETTING_KEYS, *WEATHER_KEYS, *BOOST_KEYS.values()]) if n not in FAST_VARIABLES],
        SLOW_INTERVAL,
        "slow",
    )
    await fast.async_config_entry_first_refresh()
    # what the portal said last time, to start with the local interface alone when it does not answer
    cache: Store = Store(hass, 1, f"{DOMAIN}_cache_{entry.entry_id}")
    cached = await cache.async_load() or {}
    offline = False
    if local:
        await slow.async_refresh()
        if offline := not slow.last_update_success:
            # its entities stay unavailable, but the settings are known (solar boost); full set once it answers
            slow.data = {k: Reading(v, u, tuple(s) if s else None, d) for k, (v, u, s, d) in cached.get("slow", {}).items()}
            entry.async_on_unload(slow.async_add_listener(
                lambda: slow.last_update_success and hass.config_entries.async_schedule_reload(entry.entry_id)
            ))
    else:
        await slow.async_config_entry_first_refresh()
    texts = await hass.async_add_executor_job(Texts.load, hass.config.language)
    readings = {k: r for k, r in {**fast.data, **slow.data}.items() if kind(r) != "text"}
    # the portal answers for circuits the controller does not have: leave those out
    try:
        hidden = set(cached.get("hidden", [])) if offline else hidden_groups(await client.async_read(FLAG_KEYS), readings)
    except OekofenConnectionError:
        hidden = set(cached.get("hidden", []))
    if not offline:
        await cache.async_save({"slow": slow.data, "hidden": sorted(hidden)})
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
    entry.runtime_data.main_device_id = registry.async_get_or_create(
        config_entry_id=entry.entry_id, **main_device_info(entry.entry_id, texts)
    ).id
    # devices created by earlier versions for equipment that is not there
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        ids = {identifier for domain, identifier in device.identifiers if domain == DOMAIN}
        if any(f"{entry.entry_id}_{group}" in ids for group in hidden):
            registry.async_remove_device(device.id)
    # before the platforms: a boost left by an earlier run is restored before the switch can start one
    entry.runtime_data.boost = SolarBoost(hass, entry)
    await entry.runtime_data.boost.async_start()
    # v0.12 kept its own copy of the panel history; the recorder holds it now
    await Store(hass, 1, f"{DOMAIN}_history_{entry.entry_id}").async_remove()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Unload a config entry, putting back what the solar boost changed."""
    await entry.runtime_data.boost.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> None:
    """Integration deleted: no repair or cache left behind."""
    ir.async_delete_issue(hass, DOMAIN, f"portal_unreachable_{entry.entry_id}")
    await Store(hass, 1, f"{DOMAIN}_cache_{entry.entry_id}").async_remove()
