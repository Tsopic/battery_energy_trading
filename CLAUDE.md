# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Battery Energy Trading is a **Home Assistant custom integration** for intelligent battery management and energy trading optimization. It integrates with Nord Pool electricity pricing to automatically buy energy when cheap and sell when prices are high, maximizing solar energy utilization and battery ROI.

**Prerequisites:**
- **Required**: Nord Pool integration must be installed and configured before setup
- **Optional**: Sungrow integration for automatic inverter detection and configuration

**Key Concepts:**
- Built as a HACS-compatible custom component for Home Assistant
- Analyzes 15-minute energy market slots for optimal charge/discharge timing
- Solar-first operation: prioritizes selling excess solar over grid charging
- Direct integration support for Sungrow inverters via Modbus

## Architecture

### Integration Structure

The codebase follows Home Assistant's integration pattern with these core components:

**Platform Modules** (`custom_components/battery_energy_trading/`):
- `__init__.py` - Integration setup and platform loading (sensor, binary_sensor, number, switch)
- `config_flow.py` - UI configuration flow for entity mapping
- `const.py` - Constants, defaults, and configuration keys
- `base_entity.py` - Base entity class with shared coordinator logic
- `energy_optimizer.py` - Core optimization algorithms for slot selection and arbitrage
- `automation_helper.py` - Automation script generator for Sungrow control (v0.15.0)

**Entity Platforms**:
- `sensor.py` - Discharge/charging time slots, arbitrage opportunities, automation status
- `binary_sensor.py` - Status sensors (forced_discharge, cheapest_hours, export_profitable, battery_low, solar_available)
- `number.py` - Configuration inputs (prices, hours, battery levels, rates)
- `switch.py` - Enable/disable controls (forced charging, forced discharge, export management)

### Energy Optimization Logic (`energy_optimizer.py`)

The `EnergyOptimizer` class contains core algorithms:

1. **`select_discharge_slots()`** - Selects highest-price 15-min slots for selling
   - Filters by minimum sell price threshold
   - Calculates available battery energy and discharge capacity
   - Returns slots with energy amounts and estimated revenue

2. **`select_charging_slots()`** - Selects cheapest slots for grid charging
   - Filters by maximum charge price threshold
   - Calculates needed energy to reach target battery level
   - Returns slots with energy amounts and estimated costs

3. **`calculate_arbitrage_opportunities()`** - Finds profitable charge/discharge cycles
   - Considers battery efficiency (default 90%)
   - Identifies price spreads worth exploiting
   - Returns opportunities with ROI calculations

4. **`is_current_slot_selected()`** - Checks if current time is in selected slots

### Sungrow Auto-Detection (`sungrow_helper.py`)

The `SungrowHelper` class provides automatic Sungrow integration support:

**Key Features:**
- **Entity Detection** - Automatically finds Sungrow battery level, capacity, and solar power sensors using regex patterns
- **Inverter Recognition** - Detects inverter model (SH5.0RT, SH10RT, etc.) from entity IDs or attributes
- **Spec Lookup** - Maps inverter models to charge/discharge rates (SH10RT = 10kW, SH5.0RT = 5kW)
- **Dynamic Battery Capacity** - Reads actual battery capacity from the system, works with any Sungrow-compatible battery

**Auto-Configuration Flow:**
1. `is_sungrow_integration_available()` checks for any Sungrow entities
2. `detect_sungrow_entities()` finds battery level, capacity, solar power sensors
3. `detect_inverter_model_from_entities()` identifies inverter model
4. `async_get_auto_configuration()` returns complete configuration with recommended settings

**Supported Inverters:**
- SH5.0RT/SH5.0RT-20: 5kW charge/discharge
- SH6.0RT/SH6.0RT-20: 6kW charge/discharge
- SH8.0RT/SH8.0RT-20: 8kW charge/discharge
- SH10RT/SH10RT-20: 10kW charge/discharge
- SH3.6RS, SH4.6RS, SH5.0RS, SH6.0RS

**Battery Capacity Detection:**
- Battery capacity is **dynamically read** from the `battery_capacity` entity state
- Works with any Sungrow-compatible battery regardless of model
- No hardcoded battery models - supports any capacity configuration

### DataUpdateCoordinator Pattern (`coordinator.py`)

The integration uses Home Assistant's `DataUpdateCoordinator` pattern for efficient data management:

**Implementation:**
- `BatteryEnergyTradingCoordinator` class extends `DataUpdateCoordinator[dict[str, Any]]`
- Polls Nord Pool sensor every 60 seconds via `_async_update_data()`
- Provides centralized error handling with `UpdateFailed` exceptions
- All entities inherit from `CoordinatorEntity` for automatic updates

**Benefits:**
- ✅ Single poll instead of multiple independent polls (75% reduction in API calls)
- ✅ Consistent data across all entities (no race conditions)
- ✅ Required for Home Assistant Silver tier quality scale
- ✅ Better error recovery and state management

**Coordinator Data Structure:**
```python
{
    "raw_today": list[dict],       # Today's price data from Nord Pool
    "raw_tomorrow": list[dict],    # Tomorrow's price data (after 13:00 CET)
    "current_price": float,        # Current electricity price
    # Action tracking (v0.15.0)
    "last_action": str | None,     # Last automation action (e.g., "discharge_started")
    "last_action_time": str | None, # ISO timestamp of last action
    "automation_active": bool,      # Whether automation is currently active
    "next_discharge_slot": dict | None,  # Next scheduled discharge slot
    "next_charge_slot": dict | None      # Next scheduled charge slot
}
```

### AI Module (`ai/`)

The AI subsystem provides smart battery management using machine learning:

**Components:**
- `config.py` - AIConfig dataclass for entity mappings
- `data_extractor.py` - Extract training data from HA Long-Term Statistics
- `feature_engineering.py` - Create time, lag, and rolling features
- `models/` - ML model implementations:
  - `base.py` - Abstract BaseModel interface
  - `solar_predictor.py` - GradientBoosting correction for Forecast.Solar
  - `load_forecaster.py` - Ensemble model for load prediction
  - `decision_optimizer.py` - Q-learning with epsilon-greedy policy
- `training/trainer.py` - Sequential training orchestrator (Pi 4 compatible)

**Services:**
- `train_ai_models` - Trigger model training from historical data (30-365 days)
- `get_ai_prediction` - Get current AI recommendation (CHARGE/DISCHARGE/HOLD)
- `set_ai_mode` - Enable/disable AI-driven decisions

**Memory Management:**
Sequential training with `gc.collect()` between models to stay under 500MB peak memory on Raspberry Pi 4.

**State Discretization:**
- Battery level: 5 levels (0-4, 20% each)
- Price level: 5 levels (0-4, based on percentile)
- Solar level: 4 levels (0-3)
- Load level: 3 levels (0-2)
- Hour period: 6 periods (4 hours each)

### Data Flow

1. **Config flow** - Validation and setup:
   - **Nord Pool check**: `async_step_user()` validates Nord Pool integration exists, aborts if missing
   - **Sungrow detected**: `async_step_sungrow_auto()` auto-fills entities and rates
   - **Manual**: `async_step_manual()` requires user to select entities
   - **Validation**: Selected Nord Pool entity must have `raw_today` attribute
   - **Dashboard wizard**: `async_step_dashboard()` provides dashboard import instructions after configuration
2. **Initialization** - `async_setup_entry()` creates coordinator and stores in `hass.data`
3. **Coordinator setup** - `BatteryEnergyTradingCoordinator` initialized with Nord Pool entity
4. **First refresh** - `async_config_entry_first_refresh()` loads initial data
5. **Entity creation** - All platforms receive coordinator reference for data access
6. **Configuration sensor** - `sensor.battery_energy_trading_configuration` exposes all configured entity IDs for dashboard auto-detection
7. **Number entities** - Use auto-detected charge/discharge rates from `entry.options`
8. **Coordinator polling** - Updates every 60 seconds, reads Nord Pool `raw_today`/`raw_tomorrow`
9. **Energy optimizer** - Processes coordinator data and selects optimal slots
10. **Binary sensors** - Trigger based on current time vs. selected slots
11. **Automations** - Respond to binary sensor states to control inverter

### Services

**`sync_sungrow_parameters`** - Manually refresh Sungrow auto-detected parameters
- Use case: User upgrades inverter or adds battery modules
- Automatically finds config entry with `auto_detected: true`
- Re-runs auto-detection and updates charge/discharge rates
- Called via: `service: battery_energy_trading.sync_sungrow_parameters`

**`generate_automation_scripts`** (v0.15.0) - Generate Sungrow control automations
- Generates ready-to-use YAML automations tailored to user's configuration
- Fires `battery_energy_trading_automation_generated` event for UI notification
- Optional `config_entry_id` parameter with auto-detection fallback
- Called via: `service: battery_energy_trading.generate_automation_scripts`

**`force_refresh`** (v0.15.0) - Force immediate slot recalculation
- Forces immediate recalculation of charge/discharge slots
- Useful after price data updates or configuration changes
- Called via: `service: battery_energy_trading.force_refresh`

## Common Commands

### Installation & Testing
```bash
# No build process - this is a Python-only integration
# Install by copying to Home Assistant custom_components/

# Check for Home Assistant version compatibility
cat custom_components/battery_energy_trading/manifest.json

# Validate HACS configuration
cat hacs.json

# Run tests
pytest tests/

# Run tests with coverage
pytest --cov=custom_components.battery_energy_trading --cov-report=html tests/

# Run specific test file
pytest tests/test_energy_optimizer.py -v
```

### Development

**Modern Development Workflow:**
The project uses modern Python tooling for code quality and consistency.

**Code Quality Tools:**
```bash
# Linting and formatting with Ruff (fast, all-in-one)
ruff check custom_components/battery_energy_trading/          # Check for issues
ruff check --fix custom_components/battery_energy_trading/    # Auto-fix issues
ruff format custom_components/battery_energy_trading/         # Format code

# Type checking with mypy
mypy custom_components/battery_energy_trading/

# Security scanning with bandit
bandit -r custom_components/battery_energy_trading/

# Run all checks together via pre-commit
pre-commit run --all-files
```

**Pre-commit Hooks:**
The project uses pre-commit hooks to catch issues before committing:
```bash
# Install pre-commit hooks (one-time setup)
pip install pre-commit
pre-commit install

# Hooks run automatically on git commit
# Or run manually on all files
pre-commit run --all-files
```

**Configured Hooks:**
- **Ruff** - Linting and formatting (replaces black, isort, flake8, pyupgrade)
- **Mypy** - Type checking (100% type coverage required)
- **Bandit** - Security vulnerability scanning
- **Built-in** - Trailing whitespace, end-of-file, YAML/JSON validation

**Configuration Files:**
- `ruff.toml` - Ruff linter and formatter settings (line length 100, Python 3.11+)
- `.pre-commit-config.yaml` - Pre-commit hook definitions
- `pyproject.toml` - Bandit and mypy configuration

**Development Commands:**
```bash
# Check integration structure
ls -la custom_components/battery_energy_trading/

# View integration version
grep version custom_components/battery_energy_trading/manifest.json

# Monitor logs during development
# In Home Assistant: Settings → System → Logs
# Filter by: battery_energy_trading

# Check for linting issues
ruff check custom_components/battery_energy_trading/

# Format all code
ruff format custom_components/battery_energy_trading/
```

### Release Process
```bash
# Update version in manifest.json
# Update CHANGELOG.md
# Create git tag with version number
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0
```

## Key Configuration Entities

The integration creates these entity types for user configuration:

**Number Entities** (configurable parameters):
- `number.battery_energy_trading_forced_discharge_hours` (0-24, default: 2)
  - **0 = Unlimited**: Discharge during ALL profitable slots (limited only by battery capacity)
  - **1-24**: Maximum hours to discharge (e.g., 2 = only discharge for 2 hours at highest prices)
- `number.battery_energy_trading_min_export_price` (-0.3 to 0.1 EUR, default: 0.0125)
- `number.battery_energy_trading_min_forced_sell_price` (0-0.5 EUR, default: 0.3)
- `number.battery_energy_trading_max_force_charge_price` (-0.5 to 0.2 EUR, default: 0.0)
- `number.battery_energy_trading_force_charging_hours` (0-24, default: 1)
- `number.battery_energy_trading_force_charge_target` (0-100%, default: 70)
- `number.battery_energy_trading_min_battery_level` (10-50%, default: 25)
- `number.battery_energy_trading_min_solar_threshold` (0-5000W, default: 500)
- `number.battery_energy_trading_discharge_rate_kw` (1-20 kW, auto-detected for Sungrow)
- `number.battery_energy_trading_charge_rate_kw` (1-20 kW, auto-detected for Sungrow)

**Switch Entities** (enable/disable features):
- `switch.battery_energy_trading_enable_forced_charging` (default: OFF)
- `switch.battery_energy_trading_enable_forced_discharge` (default: ON)
- `switch.battery_energy_trading_enable_export_management` (default: ON)
- `switch.battery_energy_trading_enable_multiday_optimization` (default: ON)

**Binary Sensor Entities** (automation triggers):
- `binary_sensor.battery_energy_trading_forced_discharge` - Currently in high-price slot
- `binary_sensor.battery_energy_trading_cheapest_hours` - Currently in cheap charging slot
- `binary_sensor.battery_energy_trading_low_price` - Price below export threshold
- `binary_sensor.battery_energy_trading_export_profitable` - Export is profitable
- `binary_sensor.battery_energy_trading_battery_low` - Battery below 15%
- `binary_sensor.battery_energy_trading_solar_available` - Solar production > threshold

**Sensor Entities** (information and schedules):
- `sensor.battery_energy_trading_configuration` - Diagnostic sensor exposing configured entity IDs (for dashboard auto-detection)
- `sensor.battery_energy_trading_discharge_time_slots` - Selected discharge slots with detailed attributes
- `sensor.battery_energy_trading_charging_time_slots` - Selected charging slots with detailed attributes
- `sensor.battery_energy_trading_arbitrage_opportunities` - Detected arbitrage opportunities with ROI analysis
- `sensor.battery_energy_trading_automation_status` (v0.15.0) - Real-time automation execution status
  - States: `Idle`, `Active - Discharging`, `Active - Charging`, `Unknown`
  - Attributes: `last_action`, `last_action_time`, `next_scheduled_action`, `automation_active`
- `sensor.battery_energy_trading_ai_status` (v0.16.0) - AI system status and model information
  - States: `Not Configured`, `Training`, `Ready`, `Initializing`
  - Attributes: `last_training`, `solar_model_trained`, `load_model_trained`, `decision_model_trained`, `training_metrics`

## Dashboard

The integration includes a comprehensive Lovelace dashboard with **automatic entity detection** - no manual configuration required.

### Dashboard Features

**Automatic Configuration:**
- Dashboard uses `sensor.battery_energy_trading_configuration` to auto-detect all configured entities
- Users can copy/paste the dashboard YAML without any modifications
- Nord Pool entity, battery entities, and solar entities are detected automatically via Jinja2 templates

**Dashboard Sections:**
1. **Configuration Info Card** - Shows all configured entity IDs for verification
2. **Nord Pool Price Chart** - ApexCharts visualization of today vs tomorrow prices (requires HACS card)
3. **Current Status** - Real-time operation status and binary sensor states
4. **Automation Status** (v0.15.0) - Shows automation execution state, last action, and timestamps
5. **Automation Management** (v0.15.0) - Buttons for generating automations and forcing refresh
6. **AI Status** (v0.16.0) - Shows AI training status, model readiness, and training button
7. **Daily Timeline View** - Consolidated schedule showing all discharge/charge periods for the day
8. **Operation Modes** - Enable/disable switches with inline descriptions
9. **Discharge Schedule** - Aggregate metrics + individual slot details (time, energy, price, revenue)
10. **Charging Schedule** - Aggregate metrics + individual slot details (time, energy, price, cost)
11. **Arbitrage Opportunities** - Top 5 opportunities with full breakdown (charge/discharge windows, profit, ROI)
12. **Price Thresholds** - Configure min/max prices for operations
13. **Battery Settings** - Protection levels and charge/discharge rates
14. **Solar Settings** - Minimum solar power threshold

**Dashboard Location:**
- File: `dashboards/battery_energy_trading_dashboard.yaml`
- Setup wizard in config flow provides import instructions after integration setup

**Attribute Coverage:**
- 100% of sensor attributes displayed (48/48 attributes)
- Individual time slot details visible with start/end times
- All configuration parameters accessible via UI

### Dashboard Setup

Users are guided through dashboard import via the config flow wizard:
1. Configure integration (entities detected automatically for Sungrow)
2. Dashboard setup instructions shown in final config step
3. Copy dashboard YAML from file or documentation
4. Import via Settings → Dashboards → Raw configuration editor
5. Dashboard works immediately with zero manual configuration

See `docs/dashboard-setup-guide.md` for detailed setup instructions and troubleshooting.

## Sungrow Integration

The integration has pre-built support for Sungrow SHx inverters via the [Sungrow-SHx-Inverter-Modbus-Home-Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/) integration.

**Key Sungrow Control Entities:**
- `select.sungrow_ems_mode` - Operating mode (Self-consumption, Forced Mode)
- `number.sungrow_forced_charging_power` - Force charge power (0-10000W)
- `number.sungrow_forced_discharging_power` - Force discharge power (0-10000W)
- `number.sungrow_min_soc` - Minimum battery SOC (0-100%)
- `number.sungrow_max_soc` - Maximum battery SOC (0-100%)

**Automation Pattern:**
Users create Home Assistant automations that:
1. Listen to `binary_sensor.battery_energy_trading_forced_discharge` state changes
2. Set Sungrow EMS mode to "Forced Mode" when binary sensor is ON
3. Set `number.sungrow_forced_discharging_power` to desired discharge rate (e.g., 5000W)
4. Return to "Self-consumption" mode when binary sensor is OFF

See `docs/integrations/sungrow.md` for complete automation examples.

## Important Implementation Details

### Price Data Format
Nord Pool integration provides price data via sensor attributes:
- `raw_today` - Array of today's hourly/15-min prices
- `raw_tomorrow` - Array of tomorrow's prices (available after ~13:00 CET)

Each price entry has:
```python
{
    "start": datetime,  # Slot start time
    "end": datetime,    # Slot end time
    "value": float      # Price in EUR/kWh
}
```

### 15-Minute Slot Support
The optimizer automatically detects slot duration by comparing consecutive price entries:
```python
slot_duration_hours = (prices[1]["start"] - prices[0]["start"]).total_seconds() / 3600.0
```

Energy per slot is calculated as:
```python
energy_per_slot = discharge_rate_kw * slot_duration_hours
```

### Battery Capacity Calculations
Available energy for discharge:
```python
available_energy_kwh = (battery_capacity_kwh * battery_level_percent) / 100.0
```

Max slots that can be discharged:
```python
max_discharge_slots = int(available_energy_kwh / energy_per_slot)
```

### Default Behavior
**Out of the box** (designed for solar users):
- Forced charging is **disabled** (no grid charging)
- Forced discharge is **enabled** (sell excess solar at peak prices)
- Export management is **enabled** (block export when unprofitable)

This ensures the integration is useful immediately for solar installations without risking unexpected grid charging.

## Development Notes

- All entities inherit from `BatteryEnergyTradingBaseEntity` which provides shared coordinator access
- Sensor updates happen every 60 seconds via the data coordinator
- Logging uses `_LOGGER` from Python's logging module with namespace `battery_energy_trading`
- No external Python dependencies required (uses only Home Assistant built-ins)
- Entity unique IDs are prefixed with config entry ID to support multiple instances
- All prices and calculations use EUR currency (configurable via Nord Pool integration)

## Testing

The integration has comprehensive test coverage using pytest:

### Test Structure
- `tests/conftest.py` - Shared fixtures and mock objects
- `tests/test_energy_optimizer.py` - Energy optimization algorithm tests
- `tests/test_sungrow_helper.py` - Sungrow auto-detection tests
- `tests/test_config_flow.py` - Configuration flow tests
- `tests/test_automation_helper.py` (v0.15.0) - Automation script generator tests
- `tests/test_integration_automation.py` (v0.15.0) - End-to-end automation workflow tests

### Running Tests
```bash
pytest tests/                    # Run all tests
pytest tests/ -v                 # Verbose output
pytest tests/test_energy_optimizer.py::TestEnergyOptimizer::test_select_discharge_slots_basic
```

### Coverage

**Current Status** (v0.15.0):
- **Overall Coverage**: 90.63% (exceeds 90% requirement) ✅
- **Total Tests**: 258 (all passing)
- **Test Execution Time**: ~2.5 seconds

**Coverage by Module**:
- 100% coverage (7 modules): `__init__.py`, `automation_helper.py`, `base_entity.py`, `const.py`, `coordinator.py`, `number.py`, `switch.py`
- >90% coverage (4 modules): `binary_sensor.py` (94.51%), `sungrow_helper.py` (92.59%), `sensor.py` (90.20%), `config_flow.py` (90.48%)
- Needs improvement (1 module): `energy_optimizer.py` (84.38%)

**Coverage Reporting**:
```bash
# Generate HTML coverage report
pytest --cov=custom_components.battery_energy_trading --cov-report=html tests/

# View report
open htmlcov/index.html

# Generate coverage badge
pytest --cov=custom_components.battery_energy_trading --cov-report=json tests/
```

**CI/CD Coverage Features**:
- Automatic coverage badges on push
- PR coverage comments with change tracking
- Coverage thresholds: 90% green, 70% orange, below 70% fails
- JSON and XML reports for badge generation

See `docs/development/testing.md` for detailed testing documentation and `COVERAGE_REPORT.md` for module-by-module analysis.

## Home Assistant Quality Scale

The integration follows Home Assistant's quality scale tiers to ensure professional standards:

### Current Status: Silver Tier ✅ (v0.15.0)

**Silver Tier Requirements** (all met):
- ✅ **DataUpdateCoordinator**: Implemented in `coordinator.py` with 60-second polling
- ✅ **Type hints**: 100% coverage across all modules
- ✅ **Code comments**: Comprehensive docstrings for all classes and methods
- ✅ **Async codebase**: All platforms use async/await patterns
- ✅ **Test coverage >90%**: Currently at 90.63%
- ✅ **Unique IDs**: Proper unique ID generation for all entities
- ✅ **Device registry**: DeviceInfo properly configured
- ✅ **Appropriate polling**: 60-second coordinator update interval

### Quality Improvements in v0.15.0

**New Features**:
- Automation script generator for Sungrow control (`automation_helper.py`)
- Service calls for automation management (`generate_automation_scripts`, `force_refresh`)
- Automation status monitoring sensor
- Coordinator action tracking for real-time status

**Architecture**:
- Services registered in `async_setup` per Home Assistant best practices
- Event firing for automation generation notifications
- Comprehensive coordinator action tracking

**Testing**:
- 90.63% code coverage (exceeds 90% requirement)
- 258 comprehensive tests across all platforms (+25 from v0.14.0)
- 100% coordinator.py coverage (up from 73.53%)
- Integration tests for end-to-end automation workflows

**Developer Experience**:
- Modern tooling configuration (ruff.toml, .pre-commit-config.yaml)
- Clear documentation (automatic trading setup guide)
- Automated quality checks prevent regressions

### Path to Gold Tier

**Gold Tier Requirements** (future work):
- [ ] Config flow tests for all flows (currently 90.48% coverage)
- [ ] Raise issues for custom components used
- [x] Set up code coverage reporting (✅ implemented in v0.14.0)
- [x] Implement integration tests for full workflows (✅ implemented in v0.15.0)
- [ ] Consider using common helpers from HA core

**Recommended Next Steps**:
1. Add edge case tests for energy_optimizer.py (currently 84.38%)
2. Add property-based testing for optimization algorithms
3. Improve config_flow.py coverage to 95%+

See `CODE_REVIEW_REPORT.md` for detailed quality analysis and `docs/user-guide/automatic-trading-setup.md` for v0.15.0 automation setup guide.

## Common Troubleshooting

- **Slots not selecting**: Check Nord Pool entity has `raw_today` attribute with price data
- **Battery level not updating**: Verify battery level entity ID is correct and updating
- **Solar override not working**: Check solar power entity reports watts (not kW) and threshold is set appropriately
- **Discharge not triggering**: Verify prices exceed `min_forced_sell_price` threshold and forced discharge switch is ON
- **Automation not working** (v0.15.0): Check automation status sensor for last action, verify automations were generated and enabled
- **Service call fails**: Ensure config entry is loaded, check Home Assistant logs for error details

## Documentation Workflow

### Documentation Structure

The project uses a hierarchical documentation structure:

```
docs/
├── README.md                    # Master documentation index
├── user-guide/                  # End-user documentation
├── integrations/                # Third-party integration guides
├── development/                 # Developer documentation
│   └── history/                 # Historical implementation logs
└── api/                         # API reference (in development)
```

**Key documentation files**:
- `README.md` - Project overview and quick start
- `INSTALLATION.md` - Installation guide (HACS, pip, manual)
- `CHANGELOG.md` - Version history
- `docs/DOCUMENTATION_GUIDELINES.md` - Documentation standards and workflow

### When Creating Documentation

1. **Choose the right location**:
   - User guides → `docs/user-guide/`
   - Integration guides → `docs/integrations/`
   - Developer docs → `docs/development/`
   - Implementation logs → `docs/development/history/`

2. **Follow naming conventions**:
   - Use kebab-case: `dashboard-setup.md`
   - Be descriptive: `sungrow-integration-guide.md`
   - Historical docs: `implementation-log-2025-10.md`

3. **Update index files**:
   - Add entry to directory `README.md`
   - Update `docs/README.md` if major document
   - Link from related documentation

4. **Use relative links**:
   - `[Testing Guide](../development/testing.md)`
   - `[Installation](../../INSTALLATION.md)`

### When Archiving Documentation

Move to `docs/development/history/` when:
- Implementation is complete
- Document is a historical log/diary
- Information is context, not current guidance

**Archive process**:
1. Move file to `docs/development/history/`
2. Add date stamp: `document-name-2025-10.md`
3. Update all cross-references
4. Update index files

### Before Each Release

- [ ] Update `CHANGELOG.md` with changes
- [ ] Review user-facing documentation
- [ ] Update version in `manifest.json` and `pyproject.toml`
- [ ] Verify installation guide is current
- [ ] Test all code examples
- [ ] Update `docs/README.md` if structure changed

See `docs/DOCUMENTATION_GUIDELINES.md` for complete documentation standards.
