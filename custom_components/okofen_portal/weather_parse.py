"""Parse the controller's weather forecast strings. Does not import Home Assistant.

Each string looks like ``ven., 30 oct. 13:00|15|0|13 km/h|01d|800|C`` (label, temperature, clouds %,
wind, icon, OpenWeatherMap code, unit); the first one also carries sunrise and sunset.
The label's language depends on the portal, so only the day number and the time are read from it.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, tzinfo
import re

WEATHER_KEYS = [f"LOCAL.L_weather[{i}]" for i in range(25)]
_LABEL = re.compile(r"(\d{1,2})[^\d]*?(\d{1,2}):(\d{2})\s*$")


def condition(code: int, icon: str) -> str | None:
    """OpenWeatherMap code (and day/night from the icon) -> Home Assistant weather condition."""
    if code == 800:
        return "clear-night" if icon.endswith("n") else "sunny"
    if code in (801, 802):
        return "partlycloudy"
    if code in (803, 804):
        return "cloudy"
    if 200 <= code < 300:
        return "lightning-rainy"
    if 300 <= code < 400 or 500 <= code < 600:
        if code in (502, 503, 504, 522, 531):
            return "pouring"
        return "snowy-rainy" if code == 511 else "rainy"
    if 611 <= code <= 616:
        return "snowy-rainy"
    if 600 <= code < 700:
        return "snowy"
    if code == 781:
        return "exceptional"
    if 700 <= code < 800:
        return "fog"
    return None


def _resolve(day: int, hour: int, minute: int, after: datetime, tz: tzinfo) -> datetime | None:
    """First moment with this day number and time that is not before ``after`` (minus a few hours)."""
    year, month = after.year, after.month
    for _ in range(3):
        if day <= monthrange(year, month)[1]:
            moment = datetime(year, month, day, hour, minute, tzinfo=tz)
            if moment.timestamp() >= after.timestamp() - 6 * 3600:
                return moment
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return None


def parse_forecast(items: list[str], now: datetime, tz: tzinfo) -> list[dict]:
    """The strings as a list of readings in time order; unreadable ones are skipped."""
    out: list[dict] = []
    after = now
    for item in items:
        parts = str(item).split("|")
        label = _LABEL.search(parts[0]) if parts else None
        if label is None or len(parts) < 6:
            continue
        moment = _resolve(int(label.group(1)), int(label.group(2)), int(label.group(3)), after, tz)
        if moment is None:
            continue
        after = moment
        try:
            wind = float(re.match(r"[\d.]+", parts[3]).group(0))
        except (AttributeError, ValueError):
            wind = None
        try:
            out.append(
                {
                    "datetime": moment,
                    "temperature": float(parts[1]),
                    "cloud_coverage": int(float(parts[2])),
                    "wind_speed": wind,
                    "condition": condition(int(parts[5]), parts[4]),
                }
            )
        except ValueError:
            continue
    return out


def panel_weather(readings: dict) -> dict:
    """Current sky from the controller's forecast: "ven., 30 oct. 20:56|10|0|7 km/h|01n|800|C|07:45|17:53"."""
    first = readings.get(WEATHER_KEYS[0])
    parts = str(first.value).split("|") if first is not None else []

    def part(i: int) -> str | None:
        return parts[i] if len(parts) > i else None

    def value(key: str):
        return readings[key].value if key in readings else None

    code = part(5)
    return {
        "icon": part(4),  # OpenWeatherMap icon: 01d day, 01n night
        "code": int(code) if code and code.isdigit() else None,
        "clouds": value("LOCAL.L_weather_clouds"),
        "wind": part(3),
        "sunrise": part(7),
        "sunset": part(8),
        "forecast_temp": value("LOCAL.L_weather_forecast_temp"),
        "forecast_clouds": value("LOCAL.L_weather_forecast_clouds"),
    }
