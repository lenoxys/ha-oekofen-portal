"""Bounded writes of the allow-listed settings, alone or several at once. Does not import Home Assistant."""

from __future__ import annotations

from .api import OekofenError, OekofenPortalClient, Reading
from .settings import SETTING_BY_KEY, check_number


def prepare(key: str, value: float, reading: Reading) -> tuple[int, float | int]:
    """(raw number to send, value to show) after checking the key is allowed and the value in bounds."""
    setting = SETTING_BY_KEY.get(key)
    if setting is None:
        raise ValueError(f"{key} is not an allowed setting")
    if setting.options:
        index = int(value)
        if index not in setting.options:
            raise ValueError(f"{key}: {index} is not one of {sorted(setting.options)}")
        return index, index
    check_number(setting, float(value))
    return round(float(value) * reading.divisor), float(value)


async def async_apply(
    client: OekofenPortalClient, readings: dict[str, Reading], plan: dict[str, float]
) -> dict[str, Reading]:
    """Write every setting of ``plan`` the controller has; if one fails, put the earlier ones back.

    Returns the readings with the new values. Raises OekofenError (or ValueError for a bad value
    before anything is written).
    """
    steps = []
    for key, value in plan.items():
        reading = readings.get(key)
        if reading is None:
            continue  # the controller does not have this setting
        raw, shown = prepare(key, value, reading)
        steps.append((key, raw, shown, reading))
    done: list[tuple[str, Reading]] = []
    try:
        for key, raw, _, reading in steps:
            await client.async_write(key, raw)
            done.append((key, reading))
    except OekofenError:
        for key, reading in reversed(done):  # best effort: restore what was changed
            try:
                await client.async_write(key, round(float(reading.value) * reading.divisor))
            except OekofenError:
                pass
        raise
    return {**readings, **{key: reading._replace(value=shown) for key, _, shown, reading in steps}}
