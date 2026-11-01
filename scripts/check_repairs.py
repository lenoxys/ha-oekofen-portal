"""Check the "portal unreachable" repair without a real Home Assistant.

    python scripts/check_repairs.py

Raised at once while setting up, after 3 failed reads once running, removed by the next answer;
the slow coordinator never touches it.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys
import tempfile
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "custom_components"))

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers.update_coordinator import UpdateFailed  # noqa: E402

from okofen_portal import coordinator as co  # noqa: E402
from okofen_portal.api import OekofenConnectionError, Reading  # noqa: E402

issues: set[str] = set()
co.ir.async_create_issue = lambda hass, domain, issue_id, **kw: issues.add(issue_id)
co.ir.async_delete_issue = lambda hass, domain, issue_id: issues.discard(issue_id)


class Client:
    up = False

    async def async_read(self, names):
        if not self.up:
            raise OekofenConnectionError("404, message='Not Found'")
        return {n: Reading(1.0, "", None, 1.0) for n in names}


async def read(c) -> bool:
    try:
        c.data = await c._async_update_data()
        return True
    except UpdateFailed:
        return False


async def main() -> None:
    hass = HomeAssistant(tempfile.mkdtemp())
    entry = types.SimpleNamespace(entry_id="e1", async_on_unload=lambda f: None)
    client = Client()
    fast = co.OekofenCoordinator(hass, entry, client, ["a"], co.timedelta(seconds=30), "fast")
    slow = co.OekofenCoordinator(hass, entry, client, ["b"], co.timedelta(seconds=300), "slow")
    issue = "portal_unreachable_e1"

    assert not await read(slow) and not issues, "the slow coordinator never raises it"
    assert not await read(fast) and issue in issues, "setting up: raised at once"
    client.up = True
    assert await read(fast) and not issues, "removed by the next answer"
    client.up = False
    assert not await read(fast) and not await read(fast) and not issues, "running: two failures are not enough"
    assert not await read(fast) and issue in issues, "running: raised at the third"
    client.up = True
    assert await read(slow) and issue in issues, "the slow coordinator does not remove it either"
    assert await read(fast) and not issues
    await hass.async_stop(force=True)
    print("repairs OK")


asyncio.run(main())
