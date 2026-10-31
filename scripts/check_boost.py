"""Simulate the solar boost manager (boost.py) with a fake Home Assistant and a fake portal.

    .venv/bin/python scripts/check_boost.py

Start, climbing step by step, burner stop, radiator heads saved and put back, a head or the comfort changed
by hand, someone coming home, restart in the middle of a boost, portal unreachable while restoring, stale values.
Needs the homeassistant package (imports only, no running instance).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import pathlib
import sys
import types

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "custom_components"))
from okofen_portal import boost  # noqa: E402
from okofen_portal.api import OekofenConnectionError, Reading  # noqa: E402
from okofen_portal.solar_boost import KEYS  # noqa: E402

NOW = [datetime(2026, 10, 31, 13, 0).astimezone()]
DISK: dict[str, dict] = {}  # what the fake Store saved, by key


class FakeStore:
    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        return DISK.get(self.key)

    async def async_save(self, data):
        DISK[self.key] = dict(data)

    async def async_remove(self):
        DISK.pop(self.key, None)


boost.Store = FakeStore
boost.async_track_time_interval = lambda hass, action, interval: (lambda: None)
boost.async_dispatcher_send = lambda hass, signal: None
boost.dt_util = types.SimpleNamespace(now=lambda: NOW[0])
clock = [1000.0]
boost.time = types.SimpleNamespace(monotonic=lambda: clock[0], time=lambda: NOW[0].timestamp())


class Client:
    def __init__(self):
        self.writes, self.down = [], False

    async def async_write(self, key, raw):
        if self.down:
            raise OekofenConnectionError("portal unreachable")
        self.writes.append((key, raw))


class Coordinator:
    def __init__(self, data, client=None):
        self.data, self.client, self.last_update_success = data, client, True


class Data:
    def __init__(self, values):
        self.fast = Coordinator({KEYS[k]: Reading(v, "", None, 10.0) for k, v in values.items()}, Client())
        self.slow = Coordinator({})
        self.boost = None

    def reading(self, key):
        return self.fast.data.get(key) or self.slow.data.get(key)

    def update(self, key, reading):
        self.fast.data[key] = reading

    def set(self, **values):
        for k, v in values.items():
            self.fast.data[KEYS[k]] = Reading(v, "", None, 10.0)


class State:
    def __init__(self, temperature=None, state="", **attributes):
        self.state, self.attributes = state, {"temperature": temperature, **attributes}


class Hass:
    is_running = True
    config = types.SimpleNamespace(latitude=47.25, longitude=-1.45)

    def __init__(self):
        self.states = self
        self.heads = {"climate.salon": State(20.0), "climate.radiateur_2": State(18.0)}
        self.others = {"person.a": State(state="not_home", latitude=47.3, longitude=-1.4)}  # 6 km away
        self.services = self

    def get(self, entity_id):
        return self.heads.get(entity_id) or self.others.get(entity_id)

    async def async_call(self, domain, service, data, blocking=False):
        assert (domain, service) == ("climate", "set_temperature")
        self.heads[data["entity_id"]].attributes["temperature"] = data["temperature"]


SUNNY = {
    "top": 68.0, "tank_set": 8.0, "ecs": 66.0, "ecs_set": 50.0, "room": 21.0, "comfort": 20.0, "mode": 1,
    "season": 1, "outdoor": 12.0, "heating_limit": 20.0, "flow_max": 60.0, "overshoot": 5.0,
    "forecast_clouds": 10, "cloud_limit": 55, "burner": 0, "sun": "sam., 31 oct. 13:00|15|0|9 km/h|01d|800|C|07:47|17:51",
    "room_set": 20.0, "curve_foot": 35.0, "curve_slope": 1.4,
}
COMFORT = KEYS["comfort"]


def setup():
    DISK.clear()
    hass, data = Hass(), Data(SUNNY)
    entry = types.SimpleNamespace(entry_id="e1", options={"climates": ["climate.salon", "climate.radiateur_2"], "persons": ["person.a"]}, runtime_data=data)
    manager = boost.SolarBoost(hass, entry)
    data.boost = manager
    return hass, data, entry, manager


def later(minutes):
    NOW[0] = NOW[0].replace(minute=NOW[0].minute + minutes) if NOW[0].minute + minutes < 60 else NOW[0].replace(hour=NOW[0].hour + 1, minute=NOW[0].minute + minutes - 60)
    clock[0] += minutes * 60


async def main():
    # start, then the burner starts: everything is put back at once
    NOW[0] = datetime(2026, 10, 31, 13, 0).astimezone()
    hass, data, entry, m = setup()
    await m.async_start()
    assert m.state == "inactive" and not data.fast.client.writes
    m.enabled = True
    await m.async_run()
    # starts 1 K up, the heads fully open (the highest target)
    assert m.state == "active" and data.fast.client.writes == [(COMFORT, 210)], data.fast.client.writes
    assert hass.heads["climate.salon"].attributes["temperature"] == 24 and DISK["okofen_portal_solar_boost_e1"]["heads"] == {"climate.salon": 20.0, "climate.radiateur_2": 18.0}
    later(1)
    await m.async_run()
    assert data.fast.client.writes == [(COMFORT, 210)], "no step before the controller answered (2 min)"
    for _ in range(10):  # a step every 2 min, as far as the buffer at 68 °C holds: 24 °C
        later(2)
        await m.async_run()
    assert [raw for _, raw in data.fast.client.writes] == [210, 215, 220, 225, 230, 235, 240], data.fast.client.writes
    assert DISK["okofen_portal_solar_boost_e1"]["target"] == 24.0
    # the controller now asks 67.5 °C of a 68 °C buffer: one step down at once
    data.set(tank_set=67.5)
    later(1)
    await m.async_run()
    assert data.fast.client.writes[-1] == (COMFORT, 235) and m.state == "active"
    data.set(burner=1)
    later(1)
    await m.async_run()
    assert m.state == "waiting" and m.reason == "burner" and data.fast.client.writes[-1] == (COMFORT, 200)
    assert hass.heads["climate.salon"].attributes["temperature"] == 20.0 and hass.heads["climate.radiateur_2"].attributes["temperature"] == 18.0
    assert "okofen_portal_solar_boost_e1" not in DISK
    print("démarrage à +1 K, montée par pas jusqu'à 24 °C, descente si le régulateur en demande trop, arrêt brûleur, têtes remises: OK")

    # someone comes home: the boost stops at once; no new one while they are there
    NOW[0] = datetime(2026, 10, 31, 13, 0).astimezone()
    hass, data, entry, m = setup()
    await m.async_start()
    m.enabled = True
    await m.async_run()
    assert m.state == "active"
    hass.others["person.a"] = State(state="home")
    later(1)
    await m.async_run()
    assert m.reason == "occupied" and m.session is None and data.fast.client.writes[-1] == (COMFORT, 200)
    later(30)
    await m.async_run()
    assert m.state == "waiting" and m.reason == "occupied"
    # far away (Paris): only the surplus
    hass.others["person.a"] = State(state="not_home", latitude=48.85, longitude=2.35)
    later(1)
    await m.async_run()
    assert m.reason == "far_away" and m.session is None
    print("quelqu'un rentre: arrêt immédiat; tout le monde loin: pas de surchauffe sans surplus: OK")

    # a head changed by hand is left alone; the comfort changed by hand ends the boost for the day
    NOW[0] = datetime(2026, 10, 31, 13, 0).astimezone()
    hass, data, entry, m = setup()
    await m.async_start()
    m.enabled = True
    await m.async_run()
    hass.heads["climate.radiateur_2"].attributes["temperature"] = 21.0
    data.set(comfort=22.0)
    later(1)
    await m.async_run()
    assert m.reason == "manual" and data.fast.client.writes == [(COMFORT, 210)], data.fast.client.writes
    assert hass.heads["climate.salon"].attributes["temperature"] == 20.0 and hass.heads["climate.radiateur_2"].attributes["temperature"] == 21.0
    later(30)
    await m.async_run()
    assert m.state == "waiting" and m.reason == "manual" and len(data.fast.client.writes) == 1
    print("consigne et tête changées à la main: respectées, pas de nouvelle surchauffe le même jour: OK")

    # restart in the middle of a boost: the new run restores before anything else
    NOW[0] = datetime(2026, 10, 31, 13, 0).astimezone()
    hass, data, entry, m = setup()
    await m.async_start()
    m.enabled = True
    await m.async_run()
    hass2, data2 = hass, Data({**SUNNY, "comfort": 21.0})  # what we wrote, still on the controller
    entry2 = types.SimpleNamespace(entry_id="e1", options=entry.options, runtime_data=data2)
    m2 = boost.SolarBoost(hass2, entry2)
    data2.boost = m2
    await m2.async_start()
    assert data2.fast.client.writes == [(COMFORT, 200)] and m2.session is None and m2.state == "inactive"
    assert hass2.heads["climate.salon"].attributes["temperature"] == 20.0
    print("redémarrage en pleine surchauffe: restauration d'abord: OK")

    # portal unreachable while restoring: kept on disk, retried on the reconnect schedule
    NOW[0] = datetime(2026, 10, 31, 13, 0).astimezone()
    hass, data, entry, m = setup()
    await m.async_start()
    m.enabled = True
    await m.async_run()
    data.fast.client.down = True
    await m.async_stop()
    assert m.state == "restoring" and "okofen_portal_solar_boost_e1" in DISK
    data.fast.client.down = False
    await m.async_run()  # too early: waits for the first retry delay
    assert data.fast.client.writes == [(COMFORT, 210)]
    clock[0] += 11
    await m.async_run()
    assert data.fast.client.writes[-1] == (COMFORT, 200) and m.state == "inactive" and "okofen_portal_solar_boost_e1" not in DISK
    print("portail injoignable pendant la restauration: nouvel essai, puis restauration: OK")

    # stale values (last poll failed): the boost stops
    NOW[0] = datetime(2026, 10, 31, 13, 0).astimezone()
    hass, data, entry, m = setup()
    await m.async_start()
    m.enabled = True
    await m.async_run()
    data.fast.last_update_success = False
    later(1)
    await m.async_run()
    assert m.reason == "missing_data" and m.session is None and data.fast.client.writes[-1] == (COMFORT, 200)
    print("valeurs périmées: arrêt et restauration: OK")


asyncio.run(main())
