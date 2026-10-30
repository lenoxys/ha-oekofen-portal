"""The ÖkoFEN sidebar panel: an animated schematic of the installation fed by the integration."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DASHBOARD, DOMAIN
from .names import Texts
from .weather_parse import WEATHER_KEYS

PANEL_PATH = "okofen"
STATIC_URL = f"/{DOMAIN}_static/okofen-dashboard.js"


def _weather(readings: dict) -> dict:
    """Current sky from the controller's forecast: "ven., 30 oct. 20:56|10|0|7 km/h|01n|800|C|07:45|17:53"."""
    first = readings.get(WEATHER_KEYS[0])
    parts = str(first.value).split("|") if first is not None else []

    def part(i: int) -> str | None:
        return parts[i] if len(parts) > i else None

    def value(key: str):
        return readings[key].value if key in readings else None

    code = part(5)
    return {
        "icon": part(4),  # OpenWeatherMap icon: 01d day, 01n night
        "code": int(code) if code and code.isdigit() else None,
        "clouds": value("LOCAL.L_weather_clouds"),
        "wind": part(3),
        "sunrise": part(7),
        "sunset": part(8),
        "forecast_temp": value("LOCAL.L_weather_forecast_temp"),
        "forecast_clouds": value("LOCAL.L_weather_forecast_clouds"),
    }


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
            "weather": _weather(readings),
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
