"""Try the portal client outside Home Assistant.

    OEKOFEN_USER=you@example.com OEKOFEN_PASSWORD=... python scripts/check_api.py [--roundtrip]

Needs aiohttp (pip install aiohttp). Reads the whole catalog and the writable settings and prints a
summary. With --roundtrip it also writes the *current* value of one setting back (a no-op) to check
that writing works.
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
settings = importlib.import_module("okofen_portal.settings")

FAST = ["LOCAL.L_ke_brennerkontakt_1", "LOCAL.L_ke_temp_ist", "LOCAL.L_hk[0].mischer"]
ROUNDTRIP = "LOCAL.hk[0].heizkurve_steigung"


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
        print("entités en lecture par type:", dict(kinds))

        found = await client.async_read(settings.SETTING_KEYS)
        print(f"réglages autorisés: {len(settings.SETTINGS)}, trouvés sur le contrôleur: {len(found)}")
        for s in settings.SETTINGS:
            r = found.get(s.key)
            if r is None:
                print(f"  {s.key}: ABSENT")
                continue
            inside = (
                settings.check_number(s, float(r.value)) is None
                if s.platform == "number"
                else int(r.value) in s.options
            )
            print(f"  {s.key} = {r.value!r} {r.unit} (÷{r.divisor:g}) {'dans les bornes' if inside else 'HORS BORNES'}")

        if "--roundtrip" in sys.argv:
            before = found[ROUNDTRIP]
            raw = round(float(before.value) * before.divisor)
            await client.async_write(ROUNDTRIP, raw)
            after = (await client.async_read([ROUNDTRIP]))[ROUNDTRIP]
            print(f"écriture sans effet de {ROUNDTRIP}: {before.value} -> raw {raw} -> relu {after.value}",
                  "OK" if after.value == before.value else "DIFFÉRENT")


asyncio.run(main())
