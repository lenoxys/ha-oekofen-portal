"""Presets that set several settings at once (scene entities). Does not import Home Assistant."""

from __future__ import annotations

PRESETS: dict[str, dict[str, float]] = {
    # use the surplus of the top of the buffer in the house when the sun charges it, and ask the boiler later
    "solar_priority": {
        "LOCAL.hk[0].solarheiz_temp_ein": 64,
        "LOCAL.hk[0].solarheiz_temp_aus": 60,
        "LOCAL.hk[0].solarheiz_mode": 1,  # solar pump
        "LOCAL.hk[0].ueberhoehung": 3,
    },
    # the factory-like values these settings had before
    "default": {
        "LOCAL.hk[0].solarheiz_temp_ein": 82,
        "LOCAL.hk[0].solarheiz_temp_aus": 81,
        "LOCAL.hk[0].solarheiz_mode": 0,  # schedule
        "LOCAL.hk[0].ueberhoehung": 5,
    },
}
