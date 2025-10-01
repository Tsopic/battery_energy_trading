# Changelog

All notable changes to this project will be documented in this file.

## [0.10.1] - 2025-10-01

### Fixed
- **Critical**: Entity IDs now predictable - added `suggested_object_id` to all entity classes for consistent dashboard integration
- **Critical**: Entity naming - simplified binary sensor names to match expected entity_id format
- **Critical**: Version sync completion - added VERSION import to switch.py, number.py, base_entity.py

### Changed
- All entities now use `suggested_object_id` pattern: `{domain}_{entity_type}`
- Binary sensor names simplified (e.g., "Forced Discharge Active" → "Forced Discharge")
- Entity IDs are now consistent across installations: `sensor.battery_energy_trading_configuration`

## [0.10.0] - 2025-10-01

### Changes

- fix: resolve Hassfest validation errors for CI
- fix: comprehensive code quality improvements and performance optimizations
- docs: update implementation summary with integration test coverage
- test: add comprehensive integration tests for multi-peak discharge logic
- test: fix battery state projection tests and improve test imports
- feat: implement intelligent multi-peak discharge with battery state projection
- docs: add comprehensive refactoring summary document
- docs: update CLAUDE.md with dashboard features and configuration sensor
- feat: add dashboard setup wizard to config flow
- feat: add automatic Nord Pool entity detection for dashboard
- feat: enhance dashboard with detailed time slot visibility and complete attribute coverage
- docs: add comprehensive refactoring documentation for Sungrow entity detection
- refactor: improve Sungrow entity detection accuracy based on actual modbus integration


## [0.9.0] - 2025-10-01

### Changes

- docs: add comprehensive Sungrow entity reference with modbus training data
- feat: enhance dashboard with multi-day optimization switch and detailed metrics
- docs: update release process to reflect automated workflow with repository_dispatch [skip ci]
- fix: enable automatic release workflow triggering via repository_dispatch

## [0.8.0] - 2025-10-01

### Fixed
- **Critical**: Version sync - sw_version now reads from manifest.json automatically in sensor.py and binary_sensor.py (completed in v0.8.1 for all platforms)
- **Critical**: Input validation - battery level/capacity/rate now clamped to safe ranges
- **Critical**: Division by zero - added validation for zero discharge/charge rates
- **Critical**: Cache memory leak - expired cache entries now cleaned up automatically
- **High**: Magic numbers - arbitrage threshold extracted to const.py
- **High**: Solar forecast performance - optimized datetime lookups (~66% faster)

### Changed
- Solar forecast datetime matching now uses normalized key lookups (O(1) instead of O(n))
- Cache cleanup runs automatically on each access to prevent unbounded memory growth
- `_validate_inputs()` method ensures all numeric inputs are within valid ranges

### Added
- 8 new error path tests for input validation
- Cache cleanup validation tests
- Solar forecast malformed data handling tests

### Performance
- Solar forecast processing: ~0.01ms average (from ~0.03ms)
- Cache hit rate: Excellent with 5-minute TTL
- Memory usage: Bounded with automatic cleanup

### Testing
- Total test count: 32 (all passing)
- New test coverage: Input validation, cache management, error handling


## [0.7.0] - 2025-10-01

### Changes

- feat: major performance and reliability improvements


## [0.6.1] - 2025-10-01

### Changes

- fix: critical entity registration and configuration bugs


## [0.6.0] - 2025-10-01

### Changes

- fix: add device_info to all entity classes for proper registration
- fix: add tag_name parameter to GitHub release action
- feat: add workflow_dispatch trigger to release workflow for manual releases


## [0.5.3] - 2025-10-01

### Changes

- fix: improve Sungrow entity detection and code organization
- fix: auto-release workflow now properly bumps versions from latest tag
- fix: update Sungrow entity detection patterns to match actual entity names


## [0.5.2] - 2025-10-01

### Changes

- chore: bump version to 0.5.1
- fix: remove extra optimizer argument from ForcedDischargeSensor
- fix: remove invalid 'attribute' card types from dashboard


## [0.5.0] - 2025-10-01

### Changes

- chore: bump version to 0.4.1
- ci: ignore brands validation check in HACS action
- fix: update config_flow.py to use _KW suffix constants
- feat: add Nord Pool price chart to dashboard


## [0.4.0] - 2025-10-01

### Changes

- fix: add _KW suffix to discharge and charge rate constants
- ci: add automatic release workflow on main branch commits
- docs: add HACS quick add badge to installation section
- chore: add HMB battery logo
- docs: add development status warning to README
- chore: remove temporary HACS_SETUP.md and update gitignore
- docs: add HACS validation setup instructions
- feat: major code quality improvements and Nord Pool validation
- feat: add direct Sungrow power control automations
- feat: add pre-built dashboard and Sungrow integration support
- refactor: improve code quality and add configurable rates (v0.3.0)
- feat: add automation switches and solar-first mode (v0.2.0)
- feat: intelligent 15-minute slot selection for discharge/charge
- feat: initial release of Battery Energy Trading integration


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
