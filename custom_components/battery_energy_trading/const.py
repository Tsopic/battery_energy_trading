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
SENSOR_AI_STATUS: Final = "ai_status"

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
SWITCH_ENABLE_DYNAMIC_THRESHOLDS: Final = "enable_dynamic_thresholds"
SWITCH_SIMULATION_MODE: Final = "simulation_mode"
SWITCH_SOLAR_AWARE_MODE: Final = "solar_aware_mode"
SWITCH_ENABLE_PERFORMANCE_TRACKING: Final = "enable_performance_tracking"

# Dynamic threshold settings
DEFAULT_SELL_PERCENTILE: Final = 80  # Top 20% price slots for selling
DEFAULT_BUY_PERCENTILE: Final = 20  # Bottom 20% price slots for buying
DEFAULT_MIN_SPREAD: Final = 0.05  # Minimum EUR spread for profitable trading

# Dynamic threshold sensors
SENSOR_DYNAMIC_SELL_THRESHOLD: Final = "dynamic_sell_threshold"
SENSOR_DYNAMIC_BUY_THRESHOLD: Final = "dynamic_buy_threshold"
SENSOR_PRICE_SPREAD: Final = "price_spread"
SENSOR_TRADING_RECOMMENDED: Final = "trading_recommended"

# Number types for dynamic thresholds
NUMBER_SELL_PERCENTILE: Final = "sell_percentile"
NUMBER_BUY_PERCENTILE: Final = "buy_percentile"
NUMBER_MIN_SPREAD: Final = "min_spread"

# Simulation mode sensors
SENSOR_SIMULATED_REVENUE: Final = "simulated_revenue"
SENSOR_SIMULATED_COST: Final = "simulated_cost"
SENSOR_SIMULATED_NET_PROFIT: Final = "simulated_net_profit"
SENSOR_SIMULATED_ACTIONS: Final = "simulated_actions"

# Service names for simulation
SERVICE_EXPORT_SIMULATION_DATA: Final = "export_simulation_data"
SERVICE_RESET_SIMULATION: Final = "reset_simulation"

# Solar forecast settings
DEFAULT_SOLAR_RESERVE_FACTOR: Final = 0.3  # 30% reserve for sunny days
DEFAULT_MIN_FORECAST_FOR_RESERVE: Final = 10.0  # kWh minimum for reserve mode
DEFAULT_EVENING_CONSUMPTION_ESTIMATE: Final = 5.0  # kWh

# Solar forecast sensors
SENSOR_SOLAR_FORECAST_TODAY: Final = "solar_forecast_today"
SENSOR_SOLAR_FORECAST_TOMORROW: Final = "solar_forecast_tomorrow"
SENSOR_SOLAR_INFLUENCE: Final = "solar_influence"
SENSOR_OPTIMAL_RESERVE: Final = "optimal_reserve"

# Number types for solar forecast
NUMBER_SOLAR_RESERVE_FACTOR: Final = "solar_reserve_factor"
NUMBER_EVENING_CONSUMPTION_ESTIMATE: Final = "evening_consumption_estimate"

# Performance tracking sensors
SENSOR_DAILY_PROFIT: Final = "daily_profit"
SENSOR_MONTHLY_PROFIT: Final = "monthly_profit"
SENSOR_TOTAL_PROFIT: Final = "total_profit"
SENSOR_DECISIONS_TODAY: Final = "decisions_today"
SENSOR_ENERGY_TRADED_TODAY: Final = "energy_traded_today"
SENSOR_AVG_SELL_PRICE: Final = "avg_sell_price"
SENSOR_AVG_BUY_PRICE: Final = "avg_buy_price"
SENSOR_BEST_DAY_PROFIT: Final = "best_day_profit"
SENSOR_TOTAL_ENERGY_DISCHARGED: Final = "total_energy_discharged"
SENSOR_TOTAL_ENERGY_CHARGED: Final = "total_energy_charged"

# Performance tracking services
SERVICE_EXPORT_PERFORMANCE_DATA: Final = "export_performance_data"
SERVICE_RESET_PERFORMANCE_TRACKING: Final = "reset_performance_tracking"

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
