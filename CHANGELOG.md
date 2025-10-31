# Changelog

All notable changes to this project will be documented in this file.

## [0.15.0] - 2025-10-31

### Added - Automatic Energy Trading 🤖

This release introduces **automatic automation generation** for fully automatic battery trading with complete observability and user control.

#### Core Features
- **Automation Script Generator** (`automation_helper.py`)
  - `AutomationScriptGenerator` class for generating Sungrow control automations
  - Pre-built YAML templates for discharge and charging control
  - Dynamic entity ID substitution for user configuration
  - Ready-to-use automation YAML with proper Jinja2 escaping

- **Service Calls for Automation Management**
  - `battery_energy_trading.generate_automation_scripts` - Generate automation YAML tailored to user's configuration
  - `battery_energy_trading.force_refresh` - Force immediate recalculation of charge/discharge slots
  - Services registered in `async_setup` per Home Assistant best practices
  - Event firing (`battery_energy_trading_automation_generated`) for UI notification
  - Optional `config_entry_id` parameter with auto-detection fallback

- **Automation Status Monitoring**
  - `sensor.battery_energy_trading_automation_status` - Real-time automation execution status
  - States: `Idle`, `Active - Discharging`, `Active - Charging`, `Unknown`
  - Attributes: `last_action`, `last_action_time`, `next_scheduled_action`, `automation_active`
  - Coordinator-based tracking for accurate state representation

- **Coordinator Action Tracking**
  - `record_action()` method - Track automation state changes with timestamp
  - `clear_action()` method - Reset automation status when returning to self-consumption
  - Action data included in coordinator updates for all entities
  - ISO timestamp formatting for consistent datetime handling

#### Dashboard Enhancements
- **Automation Management Section**
  - "Generate Automation Scripts" button
  - "Force Refresh Calculations" button
  - Direct service calls from dashboard UI

- **Automation Status Cards**
  - Automation status sensor in Current Status section
  - Detailed status card showing last action, timestamps, next scheduled action
  - Real-time updates via coordinator polling

#### Documentation
- **Comprehensive Automatic Trading Guide** (`docs/user-guide/automatic-trading-setup.md`)
  - Step-by-step setup instructions
  - Automation logic explanations
  - Testing procedures (dry run and live testing)
  - Troubleshooting guide
  - Best practices for solar-first and grid trading strategies
  - Customization examples

- **Updated Integration Guides**
  - Sungrow guide links to automatic setup
  - Dashboard entity reference includes new entities and services
  - Updated docs README with new guide

### Changed
- **Service Registration Architecture**: Services now registered in `async_setup` instead of `async_setup_entry` (Home Assistant best practice)
  - Allows service validation even without loaded config entries
  - Provides informative errors when configuration is missing
  - Consistent with HA core integration patterns

### Testing
- **Integration Tests** (`test_integration_automation.py`)
  - 8 comprehensive integration tests covering end-to-end flows
  - Full setup flow testing (async_setup → async_setup_entry → services)
  - Coordinator action tracking with sensor updates
  - Service call sequences (simulating dashboard button clicks)
  - End-to-end automation monitoring (10-step workflow test)
  - **Total test count**: 258 tests (all passing)

### Technical Details
- **Sensor Count**: 5 sensors (was 4) - added automation_status sensor
- **Service Count**: 3 services (was 1) - added generate_automation_scripts, force_refresh
- **Coordinator Fields**: 5 tracking fields - last_action, last_action_time, automation_active, next_discharge_slot, next_charge_slot
- **Test Coverage**: Maintained at 90%+ with 8 new integration tests
- **Code Quality**: All pre-commit hooks passing (ruff, mypy, bandit)

### Files Changed
- **New Files**:
  - `custom_components/battery_energy_trading/automation_helper.py`
  - `docs/user-guide/automatic-trading-setup.md`
  - `tests/test_automation_helper.py`
  - `tests/test_integration_automation.py`

- **Modified Files**:
  - `custom_components/battery_energy_trading/__init__.py` (service registration refactor)
  - `custom_components/battery_energy_trading/services.yaml` (new services)
  - `custom_components/battery_energy_trading/sensor.py` (AutomationStatusSensor)
  - `custom_components/battery_energy_trading/const.py` (SENSOR_AUTOMATION_STATUS)
  - `custom_components/battery_energy_trading/coordinator.py` (action tracking)
  - `dashboards/battery_energy_trading_dashboard.yaml` (automation cards)
  - `docs/integrations/sungrow.md` (automatic setup link)
  - `docs/user-guide/dashboard-entity-reference.md` (new entities/services)
  - `docs/README.md` (updated index)
  - `tests/test_init.py` (updated service tests)
  - `tests/test_sensors.py` (updated sensor count)
  - `tests/test_coordinator.py` (action tracking tests)

### User Impact
This release makes automatic battery trading **significantly easier** to set up:
- **Before**: Users manually write complex automations from examples (30-60 minutes)
- **After**: Service generates tailored automations automatically (5 minutes)
- **Monitoring**: Full visibility into automation status and last actions
- **Control**: Dashboard buttons for generation and refresh

### Upgrade Notes
No breaking changes. Existing setups continue to work unchanged. New features are opt-in via dashboard buttons or service calls.

---

## [0.12.0] - 2025-10-07

### Changes

- test: add comprehensive coordinator tests to improve coverage
- fix: run ruff format to fix code formatting
- fix: add backward-compatible ServiceCall helper for HA version compatibility
- fix: resolve test failures for Python 3.13 compatibility
- fix: resolve ruff linting errors for Python 3.13
- fix: upgrade to Python 3.13 for CI and latest dependencies
- fix: correct ruff.toml configuration syntax
- docs: update documentation for v0.14.0 release
- docs: add coverage and implementation summary reports
- feat: implement all code review recommendations and quality improvements
- fix: resolve test failures and add comprehensive code review
- refactor: consolidate base entity helpers and improve testing infrastructure
- docs: add executive refactoring summary with metrics and deployment plan
- docs: add comprehensive manual testing guide for Home Assistant integration
- docs: add comprehensive refactoring documentation for base entity consolidation
- refactor(binary_sensor): make BatteryTradingBinarySensor inherit from BatteryTradingBaseEntity
- refactor(sensor): make BatteryTradingSensor inherit from BatteryTradingBaseEntity
- feat: add three user-configurable parameters for arbitrage and battery monitoring
- feat: update arbitrage efficiency to 70% (30% loss) for realistic calculations
- feat: add partial slot discharge and user-configurable battery reserve (v0.12.0)
- feat: combine consecutive time slots for optimal battery management (v0.11.0)
- fix: complete dashboard Jinja2 template removal
- fix: replace Jinja2 templates with manual Nord Pool entity ID in dashboard


## [0.14.0] - 2025-10-06

### Added
- **DataUpdateCoordinator Implementation** ⭐ (Home Assistant Silver Tier Requirement)
  - New `coordinator.py` module with `BatteryEnergyTradingCoordinator` class
  - Centralized Nord Pool data fetching with 60-second polling interval
  - All entities now inherit from `CoordinatorEntity` for efficient data updates
  - Proper error handling with `UpdateFailed` exceptions
  - **Impact**: 75% reduction in Nord Pool sensor access, better performance, no race conditions

- **Internationalization Support**
  - German translation (`translations/de.json`)
  - Norwegian translation (`translations/no.json`)
  - Swedish translation (`translations/sv.json`)
  - Full config flow and error message translations

- **Modern Development Tools**
  - `ruff.toml` - Fast Python linter and formatter configuration (replaces black/isort)
  - `.pre-commit-config.yaml` - Pre-commit hooks for automated quality checks (ruff, mypy, bandit, YAML/JSON validation)
  - Coverage badge generation in CI/CD
  - PR coverage comments with change tracking
  - Security scanning with bandit
  - Type checking with mypy

- **Comprehensive Documentation**
  - `CODE_REVIEW_REPORT.md` (1,200+ lines) - Complete code quality analysis
  - `COVERAGE_REPORT.md` - Detailed test coverage breakdown by module
  - `IMPLEMENTATION_SUMMARY.md` - Implementation metrics and verification

### Changed
- **Base Entity Architecture**: `BatteryTradingBaseEntity` now optionally inherits from `CoordinatorEntity`
  - Backward compatible - entities without coordinator still work
  - Coordinator parameter added to all entity platform constructors
  - Integration setup now creates and initializes coordinator

- **Test Infrastructure**
  - All 233 tests updated to support coordinator architecture
  - `mock_coordinator` fixture added to `conftest.py`
  - Fixed `hass.data` to use real dict instead of MagicMock
  - Updated all sensor and binary sensor test fixtures

- **CI/CD Pipeline**
  - Lint job now uses ruff instead of black/isort
  - Added mypy type checking step
  - Added bandit security scanning
  - Coverage reporting with badges and PR comments
  - Coverage thresholds enforced (90% green, 70% orange)

### Fixed
- **Critical Test Failures**
  - Missing `CONF_SOLAR_POWER_ENTITY` import in sensor.py (caused 3 test failures)
  - Sungrow helper test false positives due to generic entity name matches

### Technical
- **Home Assistant Quality Scale**: Achieved **Silver Tier** qualification
  - ✅ DataUpdateCoordinator implemented
  - ✅ 90.51% test coverage (exceeds 90% requirement)
  - ✅ 100% type hint coverage
  - ✅ Comprehensive docstrings
  - ✅ All platforms async
  - ✅ Proper unique IDs and device registry

- **Test Coverage**: 90.51% overall (233/233 tests passing)
  - 5 modules at 100% coverage (__init__.py, base_entity.py, const.py, number.py, switch.py)
  - 4 modules >90% coverage (binary_sensor.py 94.56%, sungrow_helper.py 92.59%, sensor.py 90.94%, config_flow.py 90.55%)
  - 2 modules needing improvement (energy_optimizer.py 84.38%, coordinator.py 73.53%)

- **Code Quality**
  - Zero security vulnerabilities (bandit scan)
  - Zero linting errors (ruff)
  - 100% type coverage (mypy)
  - Pre-commit hooks prevent quality regressions

### Performance
- **Before**: Multiple independent polls to Nord Pool sensor, potential race conditions
- **After**: Single coordinated 60-second poll, all entities share same data
- **Improvement**: ~75% reduction in Nord Pool sensor access, better UI responsiveness, lower CPU usage

### Breaking Changes
**None** - All changes are backward compatible:
- ✅ Entity IDs unchanged
- ✅ Entity names unchanged
- ✅ Configuration flow unchanged
- ✅ All existing automations continue to work
- ✅ Dashboard templates remain compatible

### Developer Experience
- ✅ Automated linting and formatting (ruff)
- ✅ Pre-commit hooks catch issues before commit
- ✅ Type checking ensures type safety
- ✅ Security scanning prevents vulnerabilities
- ✅ Coverage reporting tracks test quality
- ✅ Comprehensive documentation for onboarding

## [0.13.0] - 2025-10-02

### Added
- **Three New User-Configurable Parameters**:
  - `number.battery_energy_trading_min_arbitrage_profit` - Minimum profit threshold for arbitrage detection (0.0-5.0 EUR, default 0.50)
  - `number.battery_energy_trading_battery_efficiency` - Round-trip battery efficiency for calculations (50%-95%, default 70%)
  - `number.battery_energy_trading_battery_low_threshold` - Customizable battery low warning trigger (5%-30%, default 15%)

### Changed
- **Battery Low Sensor**: Now uses configurable threshold instead of hardcoded 15%
  - Allows users to customize when low battery warning triggers
  - Entity name simplified from "Battery Below 15%" to "Battery Low"
- **Arbitrage Detection**: Now uses user-configured minimum profit and efficiency values
  - Previously used hardcoded values, now fully customizable from dashboard
  - Efficiency parameter enables calibration based on actual battery performance
- **Dashboard Updates**:
  - Added all three new number entities to dashboard
  - Reorganized "Battery Settings" section with new performance parameters
  - Updated "Price Thresholds" section title to include arbitrage

### Technical
- Added `NUMBER_MIN_ARBITRAGE_PROFIT`, `NUMBER_BATTERY_EFFICIENCY`, `NUMBER_BATTERY_LOW_THRESHOLD` constants
- Updated `ArbitrageOpportunitiesSensor` to read and pass configurable efficiency and min profit
- Updated `BatteryLowSensor` to use configurable threshold
- Dashboard now displays 13 number entities (was 10)

## [0.12.0] - 2025-10-02

### Added
- **Partial Slot Discharge**: Automatically reduces discharge amount when battery runs low to respect minimum reserve
  - Prevents battery from discharging below user-configured minimum level (10-50%, default 25%)
  - Applies to both individual slots and combined consecutive periods
  - Slot metadata includes `partial_discharge: true` flag when applied
  - Logs reduction amount and reason for transparency

### Changed
- **User-Configurable Battery Reserve**: Minimum battery level parameter now controls slot combination and partial discharge
  - Previously hardcoded to 10%, now uses dashboard-configurable value (10-50%, default 25%)
  - Configured via `number.battery_energy_trading_min_battery_level` entity
  - Visible in dashboard under "Battery Settings" → "Minimum Battery Discharge Level"
- **Arbitrage Efficiency**: Default round-trip efficiency updated from 90% to 70% (30% loss)
  - Reflects realistic energy losses from charging/discharging/inverter conversions
  - Makes arbitrage profit calculations more conservative and accurate
  - Breakdown: charging losses (~10%), discharging losses (~10%), inverter losses (~5-10%)
- Slot combination now respects user's battery protection settings
- Weighted price calculation improved for combined slots

### Technical
- `select_discharge_slots()` now accepts `min_battery_reserve_percent` parameter
- `_combine_consecutive_slots()` respects battery reserve constraints
- `_merge_slot_group()` implements partial discharge logic
- Discharge sensor retrieves and passes minimum battery level to optimizer

## [0.11.0] - 2025-10-02

### Added
- **Smart Slot Combination**: Consecutive profitable time slots are now automatically combined into longer discharge/charge periods
  - Example: Four consecutive 15-minute slots (20:00-21:00) are merged into a single 1-hour period
  - Preserves total energy, revenue/cost, and battery state across merged periods
  - Reduces number of inverter mode changes for better battery health
  - Tracked via `slot_count` attribute showing how many original slots were combined

### Fixed
- **Dashboard Configuration Card**: Fixed entity attribute display using proper markdown template syntax instead of unsupported `type: attribute` rows
  - Configuration card now uses markdown card with Jinja2 templates
  - Displays Nord Pool entity, battery entities, and solar entities correctly
  - Shows all configured entity IDs in copyable format

### Changed
- Discharge and charging slot selection now returns combined consecutive periods
- Dashboard configuration card redesigned with better visual hierarchy
- Slot metadata now includes `slot_count` to track merged periods

## [0.10.1] - 2025-10-01

### Fixed
- **Critical**: Entity IDs now predictable - added `suggested_object_id` to all entity classes for consistent dashboard integration
- **Critical**: Entity naming - simplified binary sensor names to match expected entity_id format
- **Critical**: Version sync completion - added VERSION import to switch.py, number.py, base_entity.py

### Added
- **Dashboard Enhancement**: Nord Pool price chart now overlays discharge/charge time slots with color-coded highlights
  - Red shaded areas show selected discharge slots (high price periods)
  - Green shaded areas show selected charging slots (low price periods)
  - Provides visual confirmation of optimization strategy at a glance

### Changed
- All entities now use `suggested_object_id` pattern: `{domain}_{entity_type}`
- Binary sensor names simplified (e.g., "Forced Discharge Active" → "Forced Discharge")
- Entity IDs are now consistent across installations: `sensor.battery_energy_trading_configuration`
- Dashboard price chart title updated to reflect overlay functionality

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
