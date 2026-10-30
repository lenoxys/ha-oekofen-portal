"""The ÖkoFEN sidebar panel: an animated schematic of the installation fed by the integration."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.loader import async_get_integration

from .const import DASHBOARD, DOMAIN

PANEL_PATH = "okofen"
STATIC_URL = f"/{DOMAIN}_static/okofen-dashboard.js"


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/dashboard"})
@callback
def ws_dashboard(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """The values the panel draws, from the data the integration already holds."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_loaded", "ÖkoFEN Portal is not loaded")
        return
    data = entries[0].runtime_data
    readings = {**data.slow.data, **data.fast.data}
    connection.send_result(
        msg["id"],
        {
            "language": data.texts.lang,
            "strings": data.texts.panel(),
            "values": {
                name: readings[key].value for name, key in DASHBOARD.items() if key in readings
            },
        },
    )


async def async_setup_dashboard(hass: HomeAssistant) -> None:
    """Register the websocket command and the sidebar panel (once per Home Assistant)."""
    websocket_api.async_register_command(hass, ws_dashboard)
    script = Path(__file__).parent / "frontend" / "okofen-dashboard.js"
    await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(script), False)])
    integration = await async_get_integration(hass, DOMAIN)
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="okofen-dashboard",
        frontend_url_path=PANEL_PATH,
        module_url=f"{STATIC_URL}?v={integration.version}",
        sidebar_title="ÖkoFEN",
        sidebar_icon="mdi:water-boiler",
        require_admin=False,
        config={},
    )
