# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-01-10

### Added
- **Base entity class** - Shared `BatteryTradingBaseEntity` with common helper methods
- **Configurable charge/discharge rates** - Number entities for battery charge rate (1-20 kW) and discharge rate (1-20 kW)
- **Improved error handling** - Enhanced logging and safe attribute access
- **Better observability** - Added logging throughout for easier debugging

### Changed
- **Refactored code structure** - Eliminated code duplication across sensor and binary_sensor files
- **Enhanced type safety** - Added comprehensive type hints and documentation
- **Improved logging** - Debug and warning logs for state changes and errors

### Fixed
- **Error resilience** - Graceful handling of missing entities and invalid states
- **Safer attribute access** - Protected access to Nord Pool data attributes

## [0.2.0] - 2025-01-10

### Added
- **Intelligent 15-minute slot selection** for discharge and charging
- **Battery capacity-aware scheduling** - respects available energy
- **Energy optimizer** - calculates optimal slots based on battery state
- **Automation switches** for toggling features:
  - Enable Forced Charging (default: OFF for solar-only)
  - Enable Forced Discharge (default: ON)
  - Enable Export Management (default: ON)
- **Solar-first operation mode** - designed for selling excess solar
- **Detailed slot information** in sensor attributes (time, energy, price, revenue)
- **Real-time discharge/charge detection** - binary sensors check if currently in active slot

### Changed
- **Default behavior**: Discharge enabled, charging disabled (solar-first mode)
- Sensors now show detailed 15-min slot information with energy amounts
- Binary sensors respect switch states for automation control
- Improved arbitrage detection with battery capacity consideration

### Fixed
- Slot selection now properly handles both 15-min and hourly periods
- Battery capacity calculations prevent over-scheduling

## [0.1.0] - 2025-01-10

### Added
- Initial release
- Configuration flow for easy setup
- Nord Pool price integration
- Battery level and capacity monitoring
- Optional solar power integration
- Arbitrage opportunity detection sensor
- Smart charging/discharging binary sensors
- Low price and export profitable detection
- Configurable number inputs for all parameters:
  - Forced discharge hours
  - Minimum export price
  - Minimum forced sell price
  - Maximum force charge price
  - Force charging hours
  - Force charge target
  - Minimum battery discharge level
  - Minimum solar power threshold
- Battery protection features
- Solar override capability
- Export management
- Comprehensive documentation
- HACS integration support

### Known Limitations
- Some sensor implementations are pending full completion
- Dashboard card not yet included (manual YAML configuration required)
- No historical analytics yet
- No multi-day forecasting

[0.1.0]: https://github.com/Tsopic/battery_energy_trading/releases/tag/v0.1.0
