"""Weather entity: the forecast the controller uses (OpenWeatherMap) to anticipate sunny days."""

from __future__ import annotations

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import OekofenConfigEntry
from .coordinator import OekofenCoordinator
from .entity import group_device_info
from .weather_parse import WEATHER_KEYS, parse_forecast

TEMP_KEY = "LOCAL.L_weather_temp"
CLOUDS_KEY = "LOCAL.L_weather_clouds"


PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: OekofenConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """One weather entity, if the controller has a forecast: from the local interface when it gives it."""
    data = entry.runtime_data
    coordinator = data.fast if WEATHER_KEYS[0] in data.fast.data else data.slow
    if WEATHER_KEYS[0] in coordinator.data and "weather" not in data.hidden:
        async_add_entities([OekofenWeather(coordinator)])


class OekofenWeather(CoordinatorEntity[OekofenCoordinator], WeatherEntity):
    """Current conditions and 3-hourly forecast of the controller's weather module."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_supported_features = WeatherEntityFeature.FORECAST_HOURLY

    def __init__(self, coordinator: OekofenCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_weather"
        self._attr_device_info = group_device_info(entry.entry_id, "weather", entry.runtime_data)

    @property
    def _forecast(self) -> list[dict]:
        items = [
            r.value for key in WEATHER_KEYS if (r := self.coordinator.data.get(key)) is not None
        ]
        return parse_forecast(items, dt_util.now(), dt_util.get_default_time_zone())

    @property
    def _first(self) -> dict | None:
        forecast = self._forecast
        return forecast[0] if forecast else None

    @property
    def native_temperature(self) -> float | None:
        reading = self.coordinator.data.get(TEMP_KEY)
        if reading is not None:
            return float(reading.value)
        return self._first["temperature"] if self._first else None

    @property
    def cloud_coverage(self) -> float | None:
        reading = self.coordinator.data.get(CLOUDS_KEY)
        return float(reading.value) if reading is not None else None

    @property
    def native_wind_speed(self) -> float | None:
        return self._first["wind_speed"] if self._first else None

    @property
    def condition(self) -> str | None:
        return self._first["condition"] if self._first else None

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Steps of three hours, as the controller gives them."""
        return [
            Forecast(
                datetime=step["datetime"].isoformat(),
                native_temperature=step["temperature"],
                cloud_coverage=step["cloud_coverage"],
                native_wind_speed=step["wind_speed"],
                condition=step["condition"],
            )
            for step in self._forecast
        ]

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        self.hass.async_create_task(self.async_update_listeners(("hourly",)))
