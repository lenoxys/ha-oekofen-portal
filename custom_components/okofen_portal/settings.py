"""Settings that can be written: an allow-list with bounds. Does not import Home Assistant.

Nothing outside this list can be written, and every number is checked against its bounds
before it is sent. Safety settings (collector protection, maximum temperatures of the
boiler...) are deliberately not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Setting:
    """One writable portal variable."""

    key: str  # portal name, e.g. LOCAL.hk[0].solarheiz_temp_ein
    platform: str  # "number" or "select"
    translation_key: str
    minimum: float = 0
    maximum: float = 0
    step: float = 1
    unit: str | None = None  # "°C", "K" or None
    options: dict[int, str] = field(default_factory=dict)  # select: portal index -> option slug


SETTINGS: tuple[Setting, ...] = (
    # solar discharge: spend the surplus of the top of the buffer in the house / hot water
    Setting("LOCAL.hk[0].solarheiz_temp_ein", "number", "solar_discharge_heating_start", 40, 90, 1, "°C"),
    Setting("LOCAL.hk[0].solarheiz_temp_aus", "number", "solar_discharge_heating_stop", 30, 90, 1, "°C"),
    Setting("LOCAL.hk[0].solarheiz_mode", "select", "solar_discharge_heating_mode", options={0: "schedule", 1: "solar_pump"}),
    Setting("LOCAL.ww[0].solarheiz_temp_ein", "number", "solar_discharge_hot_water_start", 40, 90, 1, "°C"),
    Setting("LOCAL.ww[0].solarheiz_temp_aus", "number", "solar_discharge_hot_water_stop", 30, 90, 1, "°C"),
    # heating circuit 1: how hot the buffer must be before the boiler is asked
    Setting("LOCAL.hk[0].ueberhoehung", "number", "heating_overshoot", 0, 15, 0.5, "K"),
    Setting("LOCAL.hk[0].vorlauftemp_max", "number", "flow_temperature_max", 30, 75, 1, "°C"),
    Setting("LOCAL.hk[0].vorlauftemp_min", "number", "flow_temperature_min", 15, 40, 1, "°C"),
    Setting("LOCAL.hk[0].heizkurve_fusspunkt", "number", "curve_base_point", 20, 60, 1, "°C"),
    Setting("LOCAL.hk[0].heizkurve_steigung", "number", "curve_slope", 0.2, 3.5, 0.1),
    Setting("LOCAL.hk[0].heizgrenze_heizen", "number", "heating_limit_comfort", 10, 30, 1, "°C"),
    Setting("LOCAL.hk[0].heizgrenze_absenken", "number", "heating_limit_setback", 5, 25, 1, "°C"),
    # summer / winter switch; "off" (0) is left out on purpose: it would stop the whole installation
    Setting("LOCAL.anlage_betriebsart", "select", "season_mode", options={1: "winter", 2: "summer"}),
)

ECO_OPTIONS = {0: "off", 1: "comfort", 2: "intermediate", 3: "ecological"}
SETTINGS += (
    # eco mode: how much the forecast lowers the room (heating) or hot water setpoint
    Setting("LOCAL.hk[0].oekomode", "select", "eco_mode_heating", options=ECO_OPTIONS),
    Setting("LOCAL.ww[0].oekomode", "select", "eco_mode_hot_water", options=ECO_OPTIONS),
)
# used by the climate and water_heater entities: mode and comfort / hot water target of each circuit
HEATING_MODES = {0: "off", 1: "auto", 2: "comfort", 3: "setback"}
HOT_WATER_MODES = {0: "off", 1: "auto", 2: "forced"}
SETTINGS += tuple(
    s
    for n in range(6)
    for s in (
        Setting(f"LOCAL.hk[{n}].betriebsart[1]", "climate", "hvac_mode", options=HEATING_MODES),
        Setting(f"LOCAL.hk[{n}].raumtemp_heizen", "climate", "comfort_target", 10, 30, 0.5, "°C"),
    )
) + tuple(
    s
    for n in range(3)
    for s in (
        Setting(f"LOCAL.ww[{n}].betriebsart[1]", "water_heater", "operation", options=HOT_WATER_MODES),
        Setting(f"LOCAL.ww[{n}].temp_heizen", "water_heater", "hot_water_target", 35, 70, 1, "°C"),
    )
)
SETTING_KEYS = [s.key for s in SETTINGS]
SETTING_BY_KEY = {s.key: s for s in SETTINGS}


def check_number(setting: Setting, value: float) -> None:
    """Raise ValueError if the value is outside the bounds of the setting."""
    if not setting.minimum <= value <= setting.maximum:
        raise ValueError(f"{setting.key}: {value} is outside {setting.minimum}..{setting.maximum}")
