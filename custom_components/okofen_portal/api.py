"""Minimal async client for the ÖkoFEN portal (my.oekofen.info).

Unofficial and read-only for now. This module does not import Home Assistant,
so it can be exercised on its own (see scripts/check_api.py).
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import aiohttp

BASE = "https://my.oekofen.info"
API = f"{BASE}/api/pwa"
_HEADERS = {"Origin": BASE, "Referer": f"{BASE}/app/"}
_CHUNK = 60  # variables per request
_PREFIX = "CAPPL:LOCAL."
_TIMEOUT = aiohttp.ClientTimeout(total=30)


class OekofenError(Exception):
    """Base error."""


class OekofenAuthError(OekofenError):
    """Wrong credentials or expired session that could not be renewed."""


class OekofenConnectionError(OekofenError):
    """The portal could not be reached or answered unexpectedly."""


class OekofenPortalClient:
    """Talk to the portal with the account's own credentials."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._client: tuple[str, str] | None = None
        self._token: str | None = None
        self._plant_id: str | None = None

    async def _discover_client(self) -> tuple[str, str]:
        """Read the web app's public OAuth client id/secret from its JavaScript."""
        try:
            async with self._session.get(f"{BASE}/app/", timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                html = await resp.text()
            main = re.search(r'src="(main\.[^"]+\.js)"', html)
            if not main:
                raise OekofenConnectionError("portal page layout changed (no main script)")
            async with self._session.get(
                f"{BASE}/app/{main.group(1)}", timeout=_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                js = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise OekofenConnectionError(str(err)) from err
        found = re.search(
            r'\.set\("client_id","([^"]+)"\)\s*,\s*\w+\.set\("client_secret","([^"]+)"\)',
            js,
        )
        if not found:
            raise OekofenConnectionError("portal OAuth client not found in the web app")
        return found.group(1), found.group(2)

    async def async_login(self) -> None:
        """Get a bearer token (OAuth2 password grant, like the web app)."""
        if self._client is None:
            self._client = await self._discover_client()
        form = aiohttp.FormData(default_to_multipart=True)
        form.add_field("grant_type", "password")
        form.add_field("client_id", self._client[0])
        form.add_field("client_secret", self._client[1])
        form.add_field("username", self._username)
        form.add_field("password", self._password)
        try:
            async with self._session.post(
                f"{API}/v1/oauth2/token", data=form, headers=_HEADERS, timeout=_TIMEOUT
            ) as resp:
                if resp.status in (400, 401, 403):
                    raise OekofenAuthError("invalid credentials")
                resp.raise_for_status()
                self._token = (await resp.json(content_type=None))["access_token"]
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError) as err:
            raise OekofenConnectionError(str(err)) from err

    async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        if self._token is None:
            await self.async_login()
        for attempt in (1, 2):
            try:
                async with self._session.request(
                    method,
                    url,
                    headers={**_HEADERS, "Authorization": f"Bearer {self._token}"},
                    timeout=_TIMEOUT,
                    **kwargs,
                ) as resp:
                    if resp.status == 401:
                        if attempt == 2:
                            raise OekofenAuthError("session refused after re-login")
                        self._token = None
                        await self.async_login()
                        continue
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise OekofenConnectionError(str(err)) from err
        raise OekofenConnectionError("unreachable")  # pragma: no cover

    async def async_plant_id(self) -> str:
        """Id of the first installation of the account."""
        if self._plant_id is None:
            data = await self._request(
                "GET", f"{API}/v3/plants", params={"limit": 10, "limitstart": 0}
            )
            plants = data.get("data", {}).get("plants", [])
            if not plants:
                raise OekofenConnectionError("no installation on this account")
            self._plant_id = str(plants[0]["id"])
        return self._plant_id

    async def async_read(self, names: list[str]) -> dict[str, float | int | str]:
        """Read variables by their name, e.g. ``L_ke_temp_ist`` (no prefix)."""
        plant = await self.async_plant_id()
        out: dict[str, float | int | str] = {}
        for i in range(0, len(names), _CHUNK):
            body = [_PREFIX + n for n in names[i : i + _CHUNK]]
            data = await self._request(
                "POST", f"{API}/v1/plants/{plant}/remotecontrol/variables", json=body
            )
            for item in data.get("data", []):
                if item.get("status") != "OK":
                    continue
                out[item["name"].removeprefix(_PREFIX)] = _value(item)
        return out


def _value(item: dict[str, Any]) -> float | int | str:
    """Apply the portal's divisor; keep text as is."""
    raw = item.get("value")
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return raw if raw is not None else ""
    divisor = item.get("divisor")
    if divisor:
        return number / float(divisor)
    return int(number) if number.is_integer() else number
