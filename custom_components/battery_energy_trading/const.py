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
