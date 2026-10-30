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
FAST_VARIABLES = list(CURATED)
MIXER_KEY = "LOCAL.L_hk[0].mischer"
MIXER_STATES = ("stopped", "opening", "closing")
