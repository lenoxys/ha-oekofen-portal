"""The ÖkoFEN sidebar panel: an animated schematic of the installation fed by the integration."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration

from .const import DASHBOARD, DOMAIN
from .history import async_points
from .names import Texts
from .weather_parse import panel_weather

PANEL_PATH = "okofen"
STATIC_URL = f"/{DOMAIN}_static/okofen-dashboard.js"
ICONS_URL = f"/{DOMAIN}_static/okofen-icons.js"


async def _panel_texts(hass: HomeAssistant, language: str | None, default: Texts) -> Texts:
    """The panel strings in the language of the user's profile (the one of the server if the user has none)."""
    if not language:
        return default
    cache: dict[str, Texts] = hass.data.setdefault(f"{DOMAIN}_panel_texts", {})
    if language not in cache:
        cache[language] = await hass.async_add_executor_job(Texts.load, language)
    return cache[language]


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/dashboard", vol.Optional("language"): str}
)
@websocket_api.async_response
async def ws_dashboard(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """The values the panel draws, from the data the integration already holds."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_loaded", "ÖkoFEN Portal is not loaded")
        return
    data = entries[0].runtime_data
    texts = await _panel_texts(hass, msg.get("language"), data.texts)
    readings = {**data.slow.data, **data.fast.data}
    connection.send_result(
        msg["id"],
        {
            "language": texts.lang,
            "strings": texts.panel(),
            "values": {
                name: readings[key].value for name, key in DASHBOARD.items() if key in readings
            },
            "weather": panel_weather(readings),
            "boost": {
                **data.boost.panel(),
                "switch": er.async_get(hass).async_get_entity_id("switch", DOMAIN, f"{entries[0].entry_id}_solar_boost"),
            },
        },
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/history"})
@websocket_api.async_response
async def ws_history(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """The last 48 h of the panel's values, from the recorder, for the replay bar and the history tab."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_loaded", "ÖkoFEN Portal is not loaded")
        return
    connection.send_result(msg["id"], await async_points(hass, entries[0].entry_id))


async def async_setup_dashboard(hass: HomeAssistant) -> None:
    """Register the websocket commands and the sidebar panel (once per Home Assistant)."""
    websocket_api.async_register_command(hass, ws_dashboard)
    websocket_api.async_register_command(hass, ws_history)
    folder = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([
        StaticPathConfig(STATIC_URL, str(folder / "okofen-dashboard.js"), False),
        StaticPathConfig(ICONS_URL, str(folder / "okofen-icons.js"), False),
    ])
    integration = await async_get_integration(hass, DOMAIN)
    # loaded on every page, so the sidebar can draw the "okofen:heat" icon before the panel is opened
    frontend.add_extra_js_url(hass, f"{ICONS_URL}?v={integration.version}")
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="okofen-dashboard",
        frontend_url_path=PANEL_PATH,
        module_url=f"{STATIC_URL}?v={integration.version}",
        sidebar_title="ÖkoFEN",
        sidebar_icon="okofen:heat",
        require_admin=False,
        config={},
    )
