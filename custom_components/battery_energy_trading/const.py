"""Constants for the Battery Energy Trading integration."""

import json
from pathlib import Path
from typing import Final


DOMAIN: Final = "battery_energy_trading"

# Read version from manifest.json
_manifest_path = Path(__file__).parent / "manifest.json"
with open(_manifest_path) as f:
    _manifest = json.load(f)
VERSION: Final = _manifest["version"]

# Configuration keys
CONF_NORDPOOL_ENTITY: Final = "nordpool_entity"
CONF_BATTERY_LEVEL_ENTITY: Final = "battery_level_entity"
CONF_BATTERY_CAPACITY_ENTITY: Final = "battery_capacity_entity"
CONF_SOLAR_POWER_ENTITY: Final = "solar_power_entity"
CONF_SOLAR_FORECAST_ENTITY: Final = "solar_forecast_entity"

# Default values
DEFAULT_MIN_EXPORT_PRICE: Final = 0.0125
DEFAULT_MIN_FORCED_SELL_PRICE: Final = 0.3
DEFAULT_MAX_FORCE_CHARGE_PRICE: Final = 0.0
DEFAULT_FORCED_DISCHARGE_HOURS: Final = 2
DEFAULT_FORCE_CHARGING_HOURS: Final = 1
DEFAULT_FORCE_CHARGE_TARGET: Final = 70
DEFAULT_MIN_BATTERY_LEVEL: Final = 25
DEFAULT_MIN_SOLAR_THRESHOLD: Final = 500
DEFAULT_DISCHARGE_RATE_KW: Final = 5.0  # kW
DEFAULT_CHARGE_RATE_KW: Final = 5.0  # kW
DEFAULT_MIN_ARBITRAGE_PROFIT: Final = 0.50  # EUR
DEFAULT_BATTERY_EFFICIENCY: Final = (
    70  # 70% round-trip efficiency (30% loss from charging/discharging/inverter losses)
)
DEFAULT_BATTERY_LOW_THRESHOLD: Final = 15  # % - Battery low warning threshold

# Sensor types
SENSOR_ARBITRAGE_OPPORTUNITIES: Final = "arbitrage_opportunities"
SENSOR_DISCHARGE_HOURS: Final = "discharge_hours"
SENSOR_CHARGING_HOURS: Final = "charging_hours"
SENSOR_PROFITABLE_HOURS: Final = "profitable_hours"
SENSOR_ECONOMICAL_HOURS: Final = "economical_hours"
SENSOR_CURRENT_OPERATION: Final = "current_operation"
SENSOR_DAILY_REVENUE: Final = "daily_revenue"
SENSOR_DAILY_COST: Final = "daily_cost"
SENSOR_AUTOMATION_STATUS: Final = "automation_status"

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
NUMBER_DISCHARGE_RATE_KW: Final = "discharge_rate_kw"
NUMBER_CHARGE_RATE_KW: Final = "charge_rate_kw"
NUMBER_MIN_ARBITRAGE_PROFIT: Final = "min_arbitrage_profit"
NUMBER_BATTERY_EFFICIENCY: Final = "battery_efficiency"
NUMBER_BATTERY_LOW_THRESHOLD: Final = "battery_low_threshold"

# Switch types
SWITCH_ENABLE_FORCED_CHARGING: Final = "enable_forced_charging"
SWITCH_ENABLE_FORCED_DISCHARGE: Final = "enable_forced_discharge"
SWITCH_ENABLE_EXPORT_MANAGEMENT: Final = "enable_export_management"
SWITCH_ENABLE_MULTIDAY_OPTIMIZATION: Final = "enable_multiday_optimization"

# Inverter control types
CONF_INVERTER_CONTROL_TYPE: Final = "inverter_control_type"
INVERTER_CONTROL_SUNGROW_MODBUS: Final = "sungrow_modbus"
INVERTER_CONTROL_SUNGROW_SCRIPTS: Final = "sungrow_scripts"
INVERTER_CONTROL_CUSTOM: Final = "custom"

# Custom control entity configuration keys
CONF_CUSTOM_DISCHARGE_SERVICE: Final = "custom_discharge_service"
CONF_CUSTOM_CHARGE_SERVICE: Final = "custom_charge_service"
CONF_CUSTOM_NORMAL_SERVICE: Final = "custom_normal_service"
CONF_CUSTOM_DISCHARGE_ENTITY: Final = "custom_discharge_entity"
CONF_CUSTOM_CHARGE_ENTITY: Final = "custom_charge_entity"
CONF_CUSTOM_NORMAL_ENTITY: Final = "custom_normal_entity"

# Default Sungrow script entities
DEFAULT_SUNGROW_SCRIPT_DISCHARGE: Final = "script.sg_set_forced_discharge_battery_mode"
DEFAULT_SUNGROW_SCRIPT_CHARGE: Final = "script.sg_set_forced_charge_battery_mode"
DEFAULT_SUNGROW_SCRIPT_NORMAL: Final = "script.sg_set_self_consumption_mode"

# Default Sungrow Modbus entities
DEFAULT_SUNGROW_MODBUS_EMS_MODE: Final = "select.sungrow_ems_mode"
DEFAULT_SUNGROW_MODBUS_DISCHARGE_POWER: Final = "number.sungrow_forced_discharging_power"
DEFAULT_SUNGROW_MODBUS_CHARGE_POWER: Final = "number.sungrow_forced_charging_power"

# Inverter control type descriptions for UI
INVERTER_CONTROL_TYPES: Final = {
    INVERTER_CONTROL_SUNGROW_MODBUS: "Sungrow Modbus (select.sungrow_ems_mode)",
    INVERTER_CONTROL_SUNGROW_SCRIPTS: "Sungrow Scripts (script.sg_set_*)",
    INVERTER_CONTROL_CUSTOM: "Custom (specify your own services)",
}
