"""Try the portal client outside Home Assistant.

    OEKOFEN_USER=you@example.com OEKOFEN_PASSWORD=... python scripts/check_api.py

Needs aiohttp (pip install aiohttp). Prints the values of the variables used by the integration.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import pathlib

import aiohttp

spec = importlib.util.spec_from_file_location(
    "api", pathlib.Path(__file__).parent.parent / "custom_components/okofen_portal/api.py"
)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

NAMES = ["L_ke_temp_ist", "L_ke_temp_soll", "L_ke_brennerkontakt_1", "L_hk[0].mischer"]


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client = api.OekofenPortalClient(
            session, os.environ["OEKOFEN_USER"], os.environ["OEKOFEN_PASSWORD"]
        )
        await client.async_login()
        print("connexion OK, installation:", "[id masqué]" if await client.async_plant_id() else "?")
        for name, value in (await client.async_read(NAMES)).items():
            print(f"  {name} = {value!r}")


asyncio.run(main())
