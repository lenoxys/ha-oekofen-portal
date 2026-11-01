"""Check the local interface path without a controller or a portal.

    python scripts/check_local_mode.py

Writes: the command sent, the echo checked, the settings the controller has go local and fall back on
the portal, the others go to the portal. Reads: the portal down, the local values go on alone, and the
repair says so (a warning, an error once the local interface fails too).
"""

from __future__ import annotations

import asyncio
import pathlib
import sys
import tempfile
import types

import aiohttp

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "custom_components"))

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers.update_coordinator import UpdateFailed  # noqa: E402

from okofen_portal import coordinator as co  # noqa: E402
from okofen_portal.api import OekofenConnectionError, OekofenPortalClient, Reading  # noqa: E402
from okofen_portal.local import OekofenLocalClient  # noqa: E402

issues: dict[str, str] = {}
co.ir.async_create_issue = lambda hass, domain, issue_id, **kw: issues.__setitem__(issue_id, kw["translation_key"])
co.ir.async_delete_issue = lambda hass, domain, issue_id: issues.pop(issue_id, None)
ALL = '{"system": {"L_ambient": 112}, "hk1": {"temp_heat": 225, "mode_auto": 2, "L_roomtemp_act": 229}}'


class Response:
    def __init__(self, text):
        self.text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    async def read(self):
        return self.text.encode("latin-1")


class Session:
    """The controller: echoes writes (or refuses with ``refuse``), answers ``all``, or is down."""

    def __init__(self):
        self.urls: list[str] = []
        self.down = False
        self.refuse = False

    def get(self, url, timeout):
        if self.down:
            raise aiohttp.ClientConnectionError("down")
        self.urls.append(url)
        command = url.rsplit("/", 1)[1]
        return Response(ALL if command == "all" else "error" if self.refuse else command + "\n")


async def writes() -> None:
    session = Session()
    local = OekofenLocalClient(session, "192.168.1.150", "pw")
    await local.async_write("LOCAL.hk[0].raumtemp_heizen", 225)
    assert session.urls[-1] == "http://192.168.1.150:4321/pw/hk1_temp_heat=225", session.urls
    await local.async_write("LOCAL.ww[0].betriebsart[1]", 2)
    assert session.urls[-1].endswith("/pw/ww1_mode_auto=2")
    session.refuse = True
    try:
        await local.async_write("LOCAL.hk[0].raumtemp_heizen", 230)
        raise AssertionError("a write the controller does not echo must fail")
    except OekofenConnectionError:
        pass
    session.refuse = False
    assert not local.writes("LOCAL.hk[0].ueberhoehung"), "the overshoot stays on the portal"

    # api.async_write: local first, portal for the rest and when the local interface fails
    client = OekofenPortalClient(None, "u", "p")
    client.local = local
    calls: list = []

    async def request(method, url, text_body=None, **kw):
        calls.append(text_body)
        return {"status": "success", "data": [{"status": "OK"}]}

    async def plant_id():
        return "P1"

    client._request, client.async_plant_id = request, plant_id
    await client.async_write("LOCAL.hk[0].raumtemp_heizen", 220)
    assert not calls and session.urls[-1].endswith("hk1_temp_heat=220"), "comfort goes local"
    await client.async_write("LOCAL.hk[0].ueberhoehung", 50)
    assert calls and "ueberhoehung" in calls[-1], "overshoot goes to the portal"
    session.down = True
    await client.async_write("LOCAL.hk[0].raumtemp_heizen", 215)
    assert "raumtemp_heizen" in calls[-1], "local down: the portal takes it"
    print("writes OK")


async def reads() -> None:
    hass = HomeAssistant(tempfile.mkdtemp())
    entry = types.SimpleNamespace(entry_id="e1", async_on_unload=lambda f: None)
    session = Session()
    local = OekofenLocalClient(session, "192.168.1.150", "pw")
    portal = OekofenPortalClient(None, "u", "p")
    portal_down = [True]

    async def portal_read(names):
        if portal_down[0]:
            raise OekofenConnectionError("404, message='Not Found'")
        return {n: Reading(1, "", None, 1.0) for n in names}

    portal.async_read = portal_read
    names = ["LOCAL.L_ke_brennerkontakt_1", "LOCAL.hk[0].raumtemp_heizen", "LOCAL.L_aussentemperatur_ist"]
    fast = co.HybridCoordinator(
        hass, entry, portal, names, co.timedelta(seconds=10), "fast", local=local, cloud_interval=co.timedelta(0)
    )
    issue = "portal_unreachable_e1"

    async def read():
        try:
            fast.data = await fast._async_update_data()
            return True
        except UpdateFailed:
            return False

    assert await read() and issues.get(issue) == "portal_unreachable_local", "setting up without the portal: local only"
    assert fast.data["LOCAL.hk[0].raumtemp_heizen"].value == 22.5 and "LOCAL.L_ke_brennerkontakt_1" not in fast.data
    portal_down[0] = False
    assert await read() and issue not in issues and "LOCAL.L_ke_brennerkontakt_1" in fast.data, "portal back"
    portal_down[0] = True
    assert await read() and await read() and "LOCAL.L_ke_brennerkontakt_1" in fast.data, "a blip keeps the portal values"
    assert issue not in issues, "no repair for a blip"
    assert await read() and "LOCAL.L_ke_brennerkontakt_1" not in fast.data, "an outage drops them (burner unknown)"
    assert issues.get(issue) == "portal_unreachable_local"
    session.down = True
    assert not await read() and issues.get(issue) == "portal_unreachable", "nothing answers: error"
    session.down, portal_down[0] = False, False
    assert await read() and issue not in issues
    await hass.async_stop(force=True)
    print("reads OK")


asyncio.run(writes())
asyncio.run(reads())
