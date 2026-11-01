"""The controller's local JSON interface (http://<host>:4321/<password>/all).

Does not import Home Assistant. It answers every few seconds without the cloud, but only knows about a
hundred variables, with its own names: ``MAP`` translates the ones the integration polls often to the
portal names, so that everything downstream stays the same. The settings of ``LOCAL_SETTINGS`` are
written here too; the rest (heating curve, solar discharge, burner...) stays on the portal.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .api import OekofenConnectionError, Reading

PORT = 4321
RATE_LIMIT = 2.6  # seconds: the controller refuses a request less than 2.5 s after the previous one
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
    # what the solar boost needs to run without the portal (same values, matched on a Touch V4.00b)
    "LOCAL.L_pu[0].einschaltfuehler_soll": ("pu1", "L_tpo_set", 10, "°C"),
    "LOCAL.L_pu[0].status": ("pu1", "L_state", 1, ""),  # status bits, 0x100: asks the boiler
    "LOCAL.L_ww[0].temp_soll": ("ww1", "L_temp_set", 10, "°C"),
    "LOCAL.L_ww[0].status": ("ww1", "L_state", 1, ""),  # 0x4000: asks the boiler
    "LOCAL.weather_limit": ("weather", "cloud_limit", 1, "%"),
    "LOCAL.L_weather_forecast_clouds": ("weather", "L_forecast_clouds", 1, "%"),
    # the controller's weather: now, and the 3-hourly forecast ("...|C|07:48|17:50": the first has sunrise and sunset)
    "LOCAL.L_weather_temp": ("weather", "L_temp", 10, "°C"),
    "LOCAL.L_weather_clouds": ("weather", "L_clouds", 1, "%"),
    "LOCAL.L_weather_forecast_temp": ("weather", "L_forecast_temp", 10, "°C"),
    "LOCAL.L_weather_forecast_today": ("weather", "L_forecast_today", 1, ""),
    "LOCAL.L_weather_time_start": ("weather", "L_starttime", 1, ""),
    "LOCAL.L_weather_time_end": ("weather", "L_endtime", 1, ""),
    **{f"LOCAL.L_weather[{i}]": ("forecast", f"L_w_{i}", 1, "") for i in range(25)},
}
# settings the controller also takes locally (same raw values as the portal: index, or tenths of a degree);
# matched on a Touch V4.00b: portal comfort 24 °C = hk1.temp_heat 240, hot water forced 55 °C = ww1 2 / 550
LOCAL_SETTINGS: dict[str, tuple[str, str, int, str]] = {
    **{
        k: v
        for n in range(6)
        for k, v in (
            (f"LOCAL.hk[{n}].betriebsart[1]", (f"hk{n + 1}", "mode_auto", 1, "")),
            (f"LOCAL.hk[{n}].raumtemp_heizen", (f"hk{n + 1}", "temp_heat", 10, "°C")),
            (f"LOCAL.hk[{n}].oekomode", (f"hk{n + 1}", "oekomode", 1, "")),
        )
    },
    **{
        k: v
        for n in range(3)
        for k, v in (
            (f"LOCAL.ww[{n}].betriebsart[1]", (f"ww{n + 1}", "mode_auto", 1, "")),
            (f"LOCAL.ww[{n}].temp_heizen", (f"ww{n + 1}", "temp_max_set", 10, "°C")),
            (f"LOCAL.ww[{n}].oekomode", (f"ww{n + 1}", "oekomode", 1, "")),
        )
    },
}
MAP.update(LOCAL_SETTINGS)


def local_url(host: str, password: str) -> str:
    """The ``all`` URL from an address ("192.168.0.10", "192.168.0.10:4321") or the full URL shown
    by the Touch ("http://192.168.0.10:4321/<password>/all"), whose password wins over ``password``."""
    host = host.strip()
    parts = urlsplit(host if "://" in host else f"http://{host}")
    path = [p for p in parts.path.split("/") if p and p not in ("all", "all?")]
    return f"http://{parts.hostname}:{parts.port or PORT}/{path[0] if path else password}/all"


class OekofenLocalClient:
    """Client of the local interface: everything of ``MAP`` read, ``LOCAL_SETTINGS`` written."""

    def __init__(self, session: aiohttp.ClientSession, host: str, password: str) -> None:
        self._url = local_url(host, password)
        self._session = session
        self._lock = asyncio.Lock()  # one request at a time, the controller refuses them too close

    async def _get(self, command: str) -> str:
        url = self._url.removesuffix("all") + command
        async with self._lock:
            try:
                for _ in range(3):  # another client (e.g. the Pellematic integration) may have just asked
                    async with self._session.get(url, timeout=_TIMEOUT) as resp:
                        resp.raise_for_status()
                        # the controller answers in latin-1 without saying so
                        text = (await resp.read()).decode("latin-1")
                    if not text.startswith("Wait at least"):
                        return text
                    await asyncio.sleep(RATE_LIMIT)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise OekofenConnectionError(f"local interface: {type(err).__name__}") from err
        raise OekofenConnectionError("local interface: busy")

    @staticmethod
    def writes(name: str) -> bool:
        return name in LOCAL_SETTINGS

    async def async_write(self, name: str, raw: int) -> None:
        """Write one setting of ``LOCAL_SETTINGS``; the controller echoes ``hk1_temp_heat=225`` when it takes it."""
        group, field, _, _ = LOCAL_SETTINGS[name]
        command = f"{group}_{field}={int(raw)}"
        if (await self._get(command)).strip() != command:
            raise OekofenConnectionError(f"local interface refused {command}")

    async def async_read(self) -> dict[str, Reading]:
        """Every variable of ``MAP`` the controller answers for, under its portal name."""
        try:
            data: dict[str, Any] = json.loads(await self._get("all"))
        except ValueError as err:
            raise OekofenConnectionError(f"local interface: {type(err).__name__}") from err
        if not isinstance(data, dict) or "system" not in data:  # e.g. "Wait at least 2500ms", wrong password
            raise OekofenConnectionError("local interface: unexpected answer")
        out: dict[str, Reading] = {}
        for key, (group, field, divisor, unit) in MAP.items():
            raw = data.get(group, {}).get(field)
            if isinstance(raw, (int, float)):
                out[key] = Reading(raw / divisor if divisor != 1 else raw, unit, None, float(divisor))
            elif isinstance(raw, str):  # the forecast
                out[key] = Reading(raw, unit, None)
        return out
