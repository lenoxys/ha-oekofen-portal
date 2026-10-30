"""Check the bounded writes, the presets and the modes without Home Assistant.

    OEKOFEN_USER=you@example.com OEKOFEN_PASSWORD=... python scripts/check_control.py [--roundtrip]

Offline part: allow-list sanity, presets inside their bounds, roll-back when a write fails.
Live part: reads the settings the climate / water heater / scenes use and shows what each preset
would change. With --roundtrip it also writes the *current* heating mode back (a no-op).
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
api, settings, control, presets = (
    importlib.import_module(f"okofen_portal.{name}") for name in ("api", "settings", "control", "presets")
)
Reading = api.Reading


def offline() -> None:
    for s in settings.SETTINGS:
        assert s.platform in ("number", "select", "climate", "water_heater"), s
        assert (s.options and not s.maximum) or (s.minimum < s.maximum and s.step > 0), s
    keys = [s.key for s in settings.SETTINGS]
    assert len(keys) == len(set(keys)), "duplicate setting"
    for name, plan in presets.PRESETS.items():
        for key, value in plan.items():
            setting = settings.SETTING_BY_KEY[key]  # must be allow-listed
            control.prepare(key, value, Reading(0, "", None, 10.0))  # and inside its bounds
    for bad in (("LOCAL.hk[0].solarheiz_temp_ein", 95), ("LOCAL.hk[0].solarheiz_mode", 5), ("LOCAL.hk[0].alias", 1)):
        try:
            control.prepare(bad[0], bad[1], Reading(0, "", None, 10.0))
            raise SystemExit(f"accepted {bad}")
        except ValueError:
            pass

    class Fake:
        def __init__(self, fail_on):
            self.calls, self.fail_on = [], fail_on

        async def async_write(self, key, raw):
            self.calls.append((key, raw))
            if len(self.calls) == self.fail_on:
                raise api.OekofenError("boom")

    readings = {k: Reading(v, "", None, 10.0) for k, v in {"LOCAL.hk[0].solarheiz_temp_ein": 82, "LOCAL.hk[0].solarheiz_temp_aus": 81, "LOCAL.hk[0].solarheiz_mode": 0, "LOCAL.hk[0].ueberhoehung": 5}.items()}
    readings["LOCAL.hk[0].solarheiz_mode"] = Reading(0, "", None, 1.0)
    ok = Fake(0)
    out = asyncio.run(control.async_apply(ok, readings, presets.PRESETS["solar_priority"]))
    assert out["LOCAL.hk[0].solarheiz_temp_ein"].value == 64 and len(ok.calls) == 4, ok.calls
    bad = Fake(3)  # the third write fails: the first two must be restored
    try:
        asyncio.run(control.async_apply(bad, readings, presets.PRESETS["solar_priority"]))
        raise SystemExit("no error raised")
    except api.OekofenError:
        pass
    assert bad.calls[3:] == [("LOCAL.hk[0].solarheiz_temp_aus", 810), ("LOCAL.hk[0].solarheiz_temp_ein", 820)], bad.calls
    print("hors ligne: liste autorisée, bornes, jeux de réglages et retour arrière OK")


async def live() -> None:
    async with aiohttp.ClientSession() as session:
        client = api.OekofenPortalClient(session, os.environ["OEKOFEN_USER"], os.environ["OEKOFEN_PASSWORD"])
        keys = [s.key for s in settings.SETTINGS if s.platform in ("climate", "water_heater")] + [
            k for plan in presets.PRESETS.values() for k in plan
        ] + ["LOCAL.L_hk[0].pumpe", "LOCAL.L_hk[0].raumtemp_ist", "LOCAL.L_ww[0].temp_soll", "LOCAL.L_ke_brennerkontakt_1"]
        data = await client.async_read(list(dict.fromkeys(keys)))
        print(f"en ligne: {len(data)} variables lues sur {len(set(keys))} demandées")
        for key in ("LOCAL.hk[0].betriebsart[1]", "LOCAL.hk[0].raumtemp_heizen", "LOCAL.L_hk[0].raumtemp_ist", "LOCAL.ww[0].betriebsart[1]", "LOCAL.ww[0].temp_heizen", "LOCAL.L_ww[0].temp_soll"):
            r = data.get(key)
            print(f"  {key:34} = {None if r is None else r.value!r} {'' if r is None else r.unit}")
        for name, plan in presets.PRESETS.items():
            diff = [(k, data[k].value, v) for k, v in plan.items() if k in data and float(data[k].value) != float(v)]
            print(f"  scène « {name} »: {len(diff)} réglage(s) changeraient:", [(k.split('.')[-1], a, '->', b) for k, a, b in diff])
        if "--roundtrip" in sys.argv:
            key = "LOCAL.hk[0].betriebsart[1]"
            raw, _ = control.prepare(key, data[key].value, data[key])
            await client.async_write(key, raw)
            again = (await client.async_read([key]))[key].value
            print(f"écriture sans effet de {key}: {data[key].value} -> {raw} -> relu {again}", "OK" if again == data[key].value else "DIFFÉRENT")


offline()
if os.environ.get("OEKOFEN_USER"):
    asyncio.run(live())
