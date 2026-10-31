"""Config flow for the ÖkoFEN Portal integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OekofenAuthError, OekofenConnectionError, OekofenPortalClient
from .const import CONF_CLIMATES, CONF_LOCAL_HOST, CONF_LOCAL_PASSWORD, DOMAIN
from .local import OekofenLocalClient
from .solar_boost import Options


def _number(minimum: float, maximum: float, step: float, unit: str) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum, max=maximum, step=step, unit_of_measurement=unit, mode=selector.NumberSelectorMode.BOX
        )
    )


DEFAULTS = Options()
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("target", default=DEFAULTS.target): _number(18, 28, 0.5, "°C"),
        vol.Optional("tank_threshold"): _number(50, 85, 0.5, "°C"),  # empty: computed from the settings
        vol.Required("hot_water_reserve", default=DEFAULTS.hot_water_reserve): _number(40, 65, 1, "°C"),
        vol.Required("after_sunrise", default=DEFAULTS.after_sunrise): _number(0, 360, 10, "min"),
        vol.Required("before_sunset", default=DEFAULTS.before_sunset): _number(0, 360, 10, "min"),
        vol.Optional(CONF_CLIMATES, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="climate", multiple=True)
        ),
    }
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_LOCAL_HOST): str,
        vol.Optional(CONF_LOCAL_PASSWORD): str,
    }
)


class OekofenPortalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the my.oekofen.info account and check it."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OekofenOptionsFlow()

    async def _validate(self, data: Mapping[str, Any]) -> tuple[str | None, str | None]:
        """Return (installation id, error key)."""
        client = OekofenPortalClient(
            async_get_clientsession(self.hass), data[CONF_USERNAME], data[CONF_PASSWORD]
        )
        try:
            await client.async_login()
            plant_id = await client.async_plant_id()
        except OekofenAuthError:
            return None, "invalid_auth"
        except OekofenConnectionError:
            return None, "cannot_connect"
        if data.get(CONF_LOCAL_HOST):  # optional local interface: check it answers
            local = OekofenLocalClient(
                async_get_clientsession(self.hass), data[CONF_LOCAL_HOST], data.get(CONF_LOCAL_PASSWORD, "")
            )
            try:
                await local.async_read()
            except OekofenConnectionError:
                return None, "cannot_connect_local"
        return plant_id, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            plant_id, error = await self._validate(user_input)
            if error is None:
                await self.async_set_unique_id(plant_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="ÖkoFEN", data=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            _, error = await self._validate(
                {CONF_USERNAME: entry.data[CONF_USERNAME], **user_input}
            )
            if error is None:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the account of an existing entry (same installation only)."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            plant_id, error = await self._validate(user_input)
            if error is None:
                await self.async_set_unique_id(plant_id)
                self._abort_if_unique_id_mismatch()
                # emptied optional fields must clear the stored values
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_LOCAL_HOST: "", CONF_LOCAL_PASSWORD: "", **user_input}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA,
                {
                    CONF_USERNAME: entry.data[CONF_USERNAME],
                    CONF_LOCAL_HOST: entry.data.get(CONF_LOCAL_HOST, ""),
                    CONF_LOCAL_PASSWORD: entry.data.get(CONF_LOCAL_PASSWORD, ""),
                }
            ),
            errors=errors,
        )


class OekofenOptionsFlow(OptionsFlow):
    """Solar boost settings (read at each check, no reload needed)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, self.config_entry.options),
        )
