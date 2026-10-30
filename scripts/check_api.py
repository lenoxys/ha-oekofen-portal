"""Try the portal client and the entity classification outside Home Assistant.

    OEKOFEN_USER=you@example.com OEKOFEN_PASSWORD=... python scripts/check_api.py

Needs aiohttp (pip install aiohttp). Reads the whole catalog once and prints a summary.
"""

from __future__ import annotations

import asyncio
import collections
import importlib
import os
import pathlib
import sys
import types

import aiohttp

# load the integration's HA-free modules as a package, without importing Home Assistant
root = pathlib.Path(__file__).parent.parent / "custom_components/okofen_portal"
pkg = types.ModuleType("okofen_portal")
pkg.__path__ = [str(root)]
sys.modules["okofen_portal"] = pkg
api = importlib.import_module("okofen_portal.api")
catalog = importlib.import_module("okofen_portal.catalog")

FAST = ["LOCAL.L_ke_brennerkontakt_1", "LOCAL.L_ke_temp_ist", "LOCAL.L_hk[0].mischer"]


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client = api.OekofenPortalClient(
            session, os.environ["OEKOFEN_USER"], os.environ["OEKOFEN_PASSWORD"]
        )
        await client.async_login()
        print("connexion OK")
        for name, reading in (await client.async_read(FAST)).items():
            print(f"  {name} = {reading.value!r} {reading.unit} {reading.states or ''}")
        names = catalog.load_catalog()
        data = await client.async_read(names)
        print(f"catalogue: {len(names)} variables, {len(data)} renvoyées par le contrôleur")
        kinds = collections.Counter(catalog.kind(r) for r in data.values())
        print("entités créées par type:", dict(kinds))
        units = collections.Counter(r.unit for r in data.values() if catalog.kind(r) == "number")
        print("unités numériques:", dict(units.most_common(10)))


asyncio.run(main())
