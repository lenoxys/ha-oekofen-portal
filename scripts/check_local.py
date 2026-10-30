"""Compare the local interface with the portal for the variables the integration reads locally.

    OEKOFEN_USER=... OEKOFEN_PASSWORD=... OEKOFEN_LOCAL_HOST=192.168.1.150 OEKOFEN_LOCAL_PASSWORD=... \
        python scripts/check_local.py
"""

from __future__ import annotations

import asyncio
import importlib
import os
import pathlib
import sys
import types

import aiohttp

root = pathlib.Path(__file__).parent.parent / "custom_components/okofen_portal"
pkg = types.ModuleType("okofen_portal")
pkg.__path__ = [str(root)]
sys.modules["okofen_portal"] = pkg
api = importlib.import_module("okofen_portal.api")
local = importlib.import_module("okofen_portal.local")


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        cloud = api.OekofenPortalClient(session, os.environ["OEKOFEN_USER"], os.environ["OEKOFEN_PASSWORD"])
        lc = local.OekofenLocalClient(session, os.environ["OEKOFEN_LOCAL_HOST"], os.environ["OEKOFEN_LOCAL_PASSWORD"])
        mine = await lc.async_read()
        theirs = await cloud.async_read(list(local.MAP))
        for key in local.MAP:
            a, b = mine.get(key), theirs.get(key)
            same = a is not None and b is not None and abs(float(a.value) - float(b.value)) <= 1
            print(f"{'ok ' if same else 'DIFF'} {key}: local={a and a.value} portal={b and b.value}")


asyncio.run(main())
