"""Constants for the ÖkoFEN Portal integration."""

from datetime import timedelta

DOMAIN = "okofen_portal"
SCAN_INTERVAL = timedelta(seconds=30)

# Portal variables (without the CAPPL:LOCAL. prefix)
VAR_BOILER_TEMP = "L_ke_temp_ist"  # existing boiler temperature, °C
VAR_BOILER_SETPOINT = "L_ke_temp_soll"  # its setpoint, °C
VAR_BURNER = "L_ke_brennerkontakt_1"  # burner contact, 0 = off, 1 = on
VAR_MIXER = "L_hk[0].mischer"  # heating circuit 1 mixing valve: 0 stop, 1 open, 2 close

VARIABLES = [VAR_BOILER_TEMP, VAR_BOILER_SETPOINT, VAR_BURNER, VAR_MIXER]
MIXER_STATES = {0: "stopped", 1: "opening", 2: "closing"}
