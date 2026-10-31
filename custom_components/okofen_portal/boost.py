"""Runs the solar boost: reads the inputs every 30 s, writes the comfort (climbing or stepping down) and the
radiator heads, restores them."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import OekofenError
from .const import CONF_ALARM, CONF_CLIMATES, CONF_PERSONS, DOMAIN, RETRY_DELAYS, RETRY_MAX
from .control import async_apply
from .solar_boost import COMFORT_KEY, KEYS, Options, checks, decide, presence

_LOGGER = logging.getLogger(__name__)
STATES = ("inactive", "waiting", "active", "restoring")


class SolarBoost:
    """One per config entry. ``session`` (also stored) is what to put back: comfort, heads; and what we wrote:
    ``target`` the comfort now, ``heads_to`` the heads, ``stepped_at`` the last step."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.signal = f"{DOMAIN}_{entry.entry_id}_boost"
        self.enabled = False  # set by the switch
        self.state = "inactive"
        self.reason = "disabled"
        self.session: dict | None = None
        self.checks: list[dict] = []  # last evaluation, shown in the panel even when switched off
        self._store: Store = Store(hass, 1, f"{DOMAIN}_solar_boost_{entry.entry_id}")
        self._changed_at: float | None = None
        self._manual_day = None  # date the user changed the comfort during a boost: no new boost that day
        self._failures = 0
        self._retry_at = 0.0
        self._lock = asyncio.Lock()
        self._unsub = None

    async def async_start(self) -> None:
        """Put back what an earlier run left (restart in the middle of a boost), then check every 30 s."""
        self.session = await self._store.async_load()
        if self.session:
            self._changed_at = self.session.get("since")
        await self.async_run()
        self._unsub = async_track_time_interval(self.hass, self._tick, timedelta(seconds=30))

    async def async_stop(self) -> None:
        """Entry unloaded: restore now; if the portal does not answer, the next start does it."""
        if self._unsub:
            self._unsub()
        self.enabled = False
        self._retry_at = 0
        await self.async_run()

    @callback
    def _tick(self, _now) -> None:
        self.hass.async_create_task(self.async_run())

    def _inputs(self) -> dict:
        data = self.entry.runtime_data
        if not data.fast.last_update_success:
            return {}  # stale values: missing data, so a running boost stops
        out = {}
        for name, key in KEYS.items():
            reading = data.reading(key)
            out[name] = None if reading is None else reading.value
        out["presence"] = self._presence()
        return out

    def _presence(self) -> str | None:
        options = self.entry.options
        alarm = self.hass.states.get(options.get(CONF_ALARM) or "")
        persons = []
        for entity_id in options.get(CONF_PERSONS, []):
            if (state := self.hass.states.get(entity_id)) is not None:
                persons.append((state.state, state.attributes.get("latitude"), state.attributes.get("longitude")))
        home = (self.hass.config.latitude, self.hass.config.longitude)
        return presence(alarm.state if alarm else None, persons, home, Options.from_dict(options).far_km)

    async def async_run(self) -> None:
        async with self._lock:
            if time.monotonic() < self._retry_at:
                return
            v = self._inputs()
            session = self.session or {}
            written, base = session.get("target"), session.get("comfort")
            now, options = dt_util.now(), Options.from_dict(self.entry.options)
            self.checks = checks(written, now, v, options, base)
            if self.enabled and not self.session and self._manual_day == now.date():
                target, self.reason = None, "manual"  # the user took over today: do not fight them
            elif self.enabled:
                target, self.reason = decide(written, self._changed_at, now, v, options, base, session.get("stepped_at"))
            else:
                target, self.reason = None, "disabled"
            want = target is not None
            try:
                if want and not self.session:
                    await self._begin(v, target)
                elif want and abs(target - written) > 0.01:
                    await self._step(target)
                elif not want and self.session:
                    await self._end(self.reason)
            except (OekofenError, HomeAssistantError, ValueError) as err:
                delay = RETRY_DELAYS[self._failures] if self._failures < len(RETRY_DELAYS) else RETRY_MAX
                self._failures += 1
                self._retry_at = time.monotonic() + delay
                _LOGGER.warning("Solar boost: write failed, next try in %s s: %s", delay, err)
            else:
                self._failures = 0
            if self.session:
                self.state = "active" if want else "restoring"
            else:
                self.state = "waiting" if self.enabled else "inactive"
            async_dispatcher_send(self.hass, self.signal)

    async def _write_comfort(self, value: float) -> None:
        data = self.entry.runtime_data
        reading = data.reading(COMFORT_KEY)
        if reading is None:
            raise HomeAssistantError("comfort setpoint not read")
        changed = await async_apply(data.fast.client, {COMFORT_KEY: reading}, {COMFORT_KEY: value})
        data.update(COMFORT_KEY, changed[COMFORT_KEY])

    async def _set_heads(self, temperatures: dict[str, float]) -> None:
        """Best effort: a head that does not answer must not block the rest."""
        for entity_id, temperature in temperatures.items():
            try:
                await self.hass.services.async_call(
                    "climate", "set_temperature", {"entity_id": entity_id, "temperature": temperature}, blocking=True
                )
            except HomeAssistantError as err:
                _LOGGER.warning("Solar boost: %s not set to %s: %s", entity_id, temperature, err)

    async def _begin(self, v: dict, target: float) -> None:
        heads_to = Options.from_dict(self.entry.options).target  # the heads fully open, the comfort climbs
        heads = {}
        for entity_id in self.entry.options.get(CONF_CLIMATES, []):
            state = self.hass.states.get(entity_id)
            if state is not None and state.attributes.get("temperature") is not None:
                heads[entity_id] = state.attributes["temperature"]
        # saved first: a restart in the middle still knows what to put back
        self.session = {"comfort": v["comfort"], "heads": heads, "target": target, "heads_to": heads_to, "since": time.time()}
        await self._store.async_save(self.session)
        try:
            await self._write_comfort(target)
        except (OekofenError, HomeAssistantError, ValueError):
            self.session = None
            await self._store.async_remove()
            raise
        self._changed_at = self.session["since"]
        await self._set_heads({entity_id: heads_to for entity_id in heads})
        _LOGGER.info("Solar boost started: comfort %s -> %s, heads %s", v["comfort"], target, list(heads))

    async def _step(self, target: float) -> None:
        """Climb or step down; the stored target only changes once written, so a failed write is tried again."""
        previous = self.session["target"]
        await self._write_comfort(target)
        self.session = {**self.session, "target": target, "stepped_at": time.time()}
        await self._store.async_save(self.session)
        _LOGGER.info("Solar boost: comfort %s -> %s", previous, target)

    async def _end(self, reason: str) -> None:
        session = self.session
        # the last value read, even when the latest poll failed (missing data is a reason to restore)
        reading = self.entry.runtime_data.reading(COMFORT_KEY)
        if reading is None:
            raise HomeAssistantError("comfort setpoint never read, cannot check it before restoring")
        # changed by hand meanwhile: keep the user's value (the same for each head)
        if abs(reading.value - session["target"]) <= 0.01:
            await self._write_comfort(session["comfort"])
        restore = {}
        for entity_id, temperature in session["heads"].items():
            state = self.hass.states.get(entity_id)
            if state is None and not self.hass.is_running:
                raise HomeAssistantError(f"{entity_id} not loaded yet")  # starting up: try again shortly
            if state is not None and state.attributes.get("temperature") == session.get("heads_to", session["target"]):
                restore[entity_id] = temperature
        await self._set_heads(restore)
        self.session = None
        self._changed_at = time.time()
        if reason == "manual":
            self._manual_day = dt_util.now().date()
        await self._store.async_remove()
        _LOGGER.info("Solar boost stopped (%s): comfort back to %s, heads %s", reason, session["comfort"], list(restore))

    def panel(self) -> dict:
        """What the panel's solar tab shows."""
        options = Options.from_dict(self.entry.options)
        return {
            "enabled": self.enabled,
            "state": self.state,
            "reason": self.reason,
            "checks": self.checks,
            "session": self.session,
            "target": options.target,
            "heads": self.entry.options.get(CONF_CLIMATES, []),
        }
