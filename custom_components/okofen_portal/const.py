"""Constants for the ÖkoFEN Portal integration."""

from datetime import timedelta

DOMAIN = "okofen_portal"
FAST_INTERVAL = timedelta(seconds=30)
SLOW_INTERVAL = timedelta(minutes=5)

# Variables that the local API does not give: enabled by default and polled fast.
# key -> (translation key, enabled by default)
CURATED = {
    "LOCAL.L_ke_brennerkontakt_1": ("burner", True),  # burner contact, 0 off / 1 on
    "LOCAL.L_ke_temp_ist": ("boiler_temperature", True),  # existing boiler, °C
    "LOCAL.L_ke_temp_soll": ("boiler_setpoint", False),
    "LOCAL.L_hk[0].mischer": ("heating_mixer", True),  # 0 stop, 1 open, 2 close
    "LOCAL.L_bestke_umschaltventil": ("boiler_valve", False),  # X24 pump/diverter output
}
# values the sidebar panel draws (short name -> variable), read every 30 s
DASHBOARD = {
    "coll": "LOCAL.L_sk[0].kollektortemp_ist",
    "tank_bottom": "LOCAL.L_sk[0].speichertemp_ist",
    "tank_top": "LOCAL.L_pu[0].einschaltfuehler_ist",
    "tank_mid": "LOCAL.L_pu[0].ausschaltfuehler_ist",
    "ecs_probe": "LOCAL.L_ww[0].einschaltfuehler_ist",
    "solar_pump": "LOCAL.L_sk[0].pumpe",
    "boiler_pump": "LOCAL.L_pu[0].pumpe",
    "heating_pump": "LOCAL.L_hk[0].pumpe",
    "flow": "LOCAL.L_hk[0].vorlauftemp_ist",
    "room": "LOCAL.L_hk[0].raumtemp_ist",
    "outdoor": "LOCAL.L_aussentemperatur_ist",
    "pool": "LOCAL.L_sk[1].speichertemp_ist",
    "pool_pump": "LOCAL.L_sk[1].pumpe",
    "burner": "LOCAL.L_ke_brennerkontakt_1",
    "boiler_temp": "LOCAL.L_ke_temp_ist",
    "mixer": "LOCAL.L_hk[0].mischer",
}
# read every 30 s for the climate and water_heater entities of the first circuits
CLIMATE_FAST = [
    "LOCAL.L_hk[0].raumtemp_soll",
    "LOCAL.L_hk[0].vorlauftemp_soll",
    "LOCAL.L_hk[0].status",
    "LOCAL.hk[0].betriebsart[1]",
    "LOCAL.hk[0].raumtemp_heizen",
    "LOCAL.ww[0].betriebsart[1]",
    "LOCAL.ww[0].temp_heizen",
]
FAST_VARIABLES = list(dict.fromkeys([*CURATED, *DASHBOARD.values(), *CLIMATE_FAST]))
MIXER_KEY = "LOCAL.L_hk[0].mischer"
MIXER_STATES = ("stopped", "opening", "closing")

# variables shown through a dedicated entity or a translated name
TRANSLATED = {"LOCAL.L_weather_forecast_today": "forecast_day"}
FORECAST_DAY_KEY = "LOCAL.L_weather_forecast_today"
FORECAST_DAY_STATES = ("today", "tomorrow")
CLOCK_KEYS = {  # times stored as HHMM numbers (1750 = 17:50)
    "LOCAL.L_weather_time_start",
    "LOCAL.L_weather_time_end",
    "LOCAL.L_weather_comfort_start",
    "LOCAL.L_weather_comfort_end",
}
COVERED_BY_WEATHER = {"LOCAL.L_weather_temp", "LOCAL.L_weather_clouds"}  # already in the weather entity
