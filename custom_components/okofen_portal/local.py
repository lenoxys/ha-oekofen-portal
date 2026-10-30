"""The controller's local JSON interface (http://<host>:4321/<password>/all).

Does not import Home Assistant. It answers every few seconds without the cloud, but only knows about a
hundred variables, with its own names: ``MAP`` translates the ones the integration polls often to the
portal names, so that everything downstream stays the same. Writes and the rest stay on the portal.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

from .api import OekofenConnectionError, Reading

PORT = 4321
_TIMEOUT = aiohttp.ClientTimeout(total=10)

# portal variable -> (group, field, divisor, unit) of the local interface; the values are integers
# (temperatures in tenths of a degree), the controller only gives that without the metadata of ``all?``,
# which the HTTP client cannot ask for (it drops the empty query)
MAP: dict[str, tuple[str, str, int, str]] = {
    "LOCAL.L_aussentemperatur_ist": ("system", "L_ambient", 10, "°C"),
    "LOCAL.L_sk[0].kollektortemp_ist": ("sk1", "L_koll_temp", 10, "°C"),
    "LOCAL.L_sk[0].speichertemp_ist": ("sk1", "L_spu", 10, "°C"),
    "LOCAL.L_sk[0].pumpe": ("sk1", "L_pump", 1, ""),
    "LOCAL.L_sk[1].speichertemp_ist": ("sk2", "L_spu", 10, "°C"),
    "LOCAL.L_sk[1].pumpe": ("sk2", "L_pump", 1, ""),
    "LOCAL.L_pu[0].einschaltfuehler_ist": ("pu1", "L_tpo_act", 10, "°C"),
    "LOCAL.L_pu[0].ausschaltfuehler_ist": ("pu1", "L_tpm_act", 10, "°C"),
    "LOCAL.L_pu[0].pumpe": ("pu1", "L_pump", 1, ""),
    "LOCAL.L_ww[0].einschaltfuehler_ist": ("ww1", "L_ontemp_act", 10, "°C"),
    "LOCAL.L_hk[0].pumpe": ("hk1", "L_pump", 1, ""),
    "LOCAL.L_hk[0].vorlauftemp_ist": ("hk1", "L_flowtemp_act", 10, "°C"),
    "LOCAL.L_hk[0].vorlauftemp_soll": ("hk1", "L_flowtemp_set", 10, "°C"),
    "LOCAL.L_hk[0].raumtemp_ist": ("hk1", "L_roomtemp_act", 10, "°C"),
    "LOCAL.L_hk[0].raumtemp_soll": ("hk1", "L_roomtemp_set", 10, "°C"),
}


class OekofenLocalClient:
    """Read-only client of the local interface."""

    def __init__(self, session: aiohttp.ClientSession, host: str, password: str) -> None:
        host = host.strip().removeprefix("http://").rstrip("/")
        self._url = f"http://{host if ':' in host else f'{host}:{PORT}'}/{password}/all"
        self._session = session

    async def async_read(self) -> dict[str, Reading]:
        """Every variable of ``MAP`` the controller answers for, under its portal name."""
        try:
            async with self._session.get(self._url, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                # the controller answers in latin-1 without saying so
                data: dict[str, Any] = json.loads((await resp.read()).decode("latin-1"))
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise OekofenConnectionError(f"local interface: {type(err).__name__}") from err
        if not isinstance(data, dict) or "system" not in data:  # e.g. "Wait at least 2500ms", wrong password
            raise OekofenConnectionError("local interface: unexpected answer")
        out: dict[str, Reading] = {}
        for key, (group, field, divisor, unit) in MAP.items():
            raw = data.get(group, {}).get(field)
            if isinstance(raw, (int, float)):
                out[key] = Reading(raw / divisor if divisor != 1 else raw, unit, None, float(divisor))
        return out
