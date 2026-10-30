"""Config flow for the ÖkoFEN Portal integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OekofenAuthError, OekofenConnectionError, OekofenPortalClient
from .const import DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


class OekofenPortalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the my.oekofen.info account and check it."""

    VERSION = 1

    async def _validate(self, data: Mapping[str, Any]) -> tuple[str | None, str | None]:
        """Return (installation id, error key)."""
        client = OekofenPortalClient(
            async_get_clientsession(self.hass), data[CONF_USERNAME], data[CONF_PASSWORD]
        )
        try:
            await client.async_login()
            return await client.async_plant_id(), None
        except OekofenAuthError:
            return None, "invalid_auth"
        except OekofenConnectionError:
            return None, "cannot_connect"

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
