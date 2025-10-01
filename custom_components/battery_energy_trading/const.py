"""Constants for the Battery Energy Trading integration."""
from typing import Final

DOMAIN: Final = "battery_energy_trading"

# Configuration keys
CONF_NORDPOOL_ENTITY: Final = "nordpool_entity"
CONF_BATTERY_LEVEL_ENTITY: Final = "battery_level_entity"
CONF_BATTERY_CAPACITY_ENTITY: Final = "battery_capacity_entity"
CONF_SOLAR_POWER_ENTITY: Final = "solar_power_entity"

# Default values
DEFAULT_MIN_EXPORT_PRICE: Final = 0.0125
DEFAULT_MIN_FORCED_SELL_PRICE: Final = 0.3
DEFAULT_MAX_FORCE_CHARGE_PRICE: Final = 0.0
DEFAULT_FORCED_DISCHARGE_HOURS: Final = 2
DEFAULT_FORCE_CHARGING_HOURS: Final = 1
DEFAULT_FORCE_CHARGE_TARGET: Final = 70
DEFAULT_MIN_BATTERY_LEVEL: Final = 25
DEFAULT_MIN_SOLAR_THRESHOLD: Final = 500

# Sensor types
SENSOR_ARBITRAGE_OPPORTUNITIES: Final = "arbitrage_opportunities"
SENSOR_DISCHARGE_HOURS: Final = "discharge_hours"
SENSOR_CHARGING_HOURS: Final = "charging_hours"
SENSOR_PROFITABLE_HOURS: Final = "profitable_hours"
SENSOR_ECONOMICAL_HOURS: Final = "economical_hours"

# Binary sensor types
BINARY_SENSOR_FORCED_DISCHARGE: Final = "forced_discharge"
BINARY_SENSOR_LOW_PRICE: Final = "low_price"
BINARY_SENSOR_EXPORT_PROFITABLE: Final = "export_profitable"
BINARY_SENSOR_CHEAPEST_HOURS: Final = "cheapest_hours"
BINARY_SENSOR_BATTERY_LOW: Final = "battery_low"
BINARY_SENSOR_SOLAR_AVAILABLE: Final = "solar_available"

# Number input types
NUMBER_FORCED_DISCHARGE_HOURS: Final = "forced_discharge_hours"
NUMBER_MIN_EXPORT_PRICE: Final = "min_export_price"
NUMBER_MIN_FORCED_SELL_PRICE: Final = "min_forced_sell_price"
NUMBER_MAX_FORCE_CHARGE_PRICE: Final = "max_force_charge_price"
NUMBER_FORCE_CHARGING_HOURS: Final = "force_charging_hours"
NUMBER_FORCE_CHARGE_TARGET: Final = "force_charge_target"
NUMBER_MIN_BATTERY_LEVEL: Final = "min_battery_level"
NUMBER_MIN_SOLAR_THRESHOLD: Final = "min_solar_threshold"

# Switch types
SWITCH_ENABLE_FORCED_CHARGING: Final = "enable_forced_charging"
SWITCH_ENABLE_FORCED_DISCHARGE: Final = "enable_forced_discharge"
SWITCH_ENABLE_EXPORT_MANAGEMENT: Final = "enable_export_management"
