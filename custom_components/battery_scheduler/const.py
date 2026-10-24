"""Konstanten für die Battery-Scheduler-Integration."""

from datetime import time

DOMAIN = "battery_scheduler"

# Konfiguration (Config-Flow / Optionen)
CONF_SOC_SENSOR = "soc_sensor"
CONF_GRID_SENSOR = "grid_sensor"
CONF_CHARGE_ENTITY = "charge_power_entity"
CONF_DISCHARGE_ENTITY = "discharge_power_entity"
CONF_GRID_INVERT = "grid_invert"
CONF_SETPOINT_INVERT = "setpoint_invert"
CONF_TARGET_GRID = "target_grid_power"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_NAME = "Batteriespeicher"
DEFAULT_TARGET_GRID = 10
DEFAULT_UPDATE_INTERVAL = 10

# Hartes Leistungslimit (Balkonkraftwerk / 800-W-Grenze)
MAX_POWER = 800

# Standardwerte der Einstellungen
DEFAULT_MIN_SOC = 10
DEFAULT_MAX_SOC = 100
DEFAULT_MAX_CHARGE = MAX_POWER
DEFAULT_MAX_DISCHARGE = MAX_POWER
DEFAULT_CHARGE_START = time(10, 0)
DEFAULT_CHARGE_END = time(16, 0)
DEFAULT_DISCHARGE_START = time(18, 0)
DEFAULT_DISCHARGE_END = time(7, 0)

# Regelparameter
SOC_HYSTERESIS = 2  # % – verhindert Flattern an Min-/Max-Grenze
DEADBAND = 10  # W – kleinere Änderungen werden nicht geschrieben

# Betriebsmodi
MODE_DISABLED = "disabled"
MODE_IDLE = "idle"
MODE_CHARGING = "charging"
MODE_FULL = "full"
MODE_DISCHARGING = "discharging"
MODE_EMPTY = "empty"
MODE_ERROR = "error"

MODES = [
    MODE_DISABLED,
    MODE_IDLE,
    MODE_CHARGING,
    MODE_FULL,
    MODE_DISCHARGING,
    MODE_EMPTY,
    MODE_ERROR,
]
