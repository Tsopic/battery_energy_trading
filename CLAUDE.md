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

**Entity Platforms**:
- `sensor.py` - Discharge/charging time slots, arbitrage opportunities
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

### Data Flow

1. **Config flow** - Validation and setup:
   - **Nord Pool check**: `async_step_user()` validates Nord Pool integration exists, aborts if missing
   - **Sungrow detected**: `async_step_sungrow_auto()` auto-fills entities and rates
   - **Manual**: `async_step_manual()` requires user to select entities
   - **Validation**: Selected Nord Pool entity must have `raw_today` attribute
   - **Dashboard wizard**: `async_step_dashboard()` provides dashboard import instructions after configuration
2. **Initialization** - `async_setup_entry()` stores data + options (including auto-detected rates)
3. **Configuration sensor** - `sensor.battery_energy_trading_configuration` exposes all configured entity IDs for dashboard auto-detection
4. **Number entities** - Use auto-detected charge/discharge rates from `entry.options`
5. **Coordinator** - Polls every 60 seconds, reads Nord Pool `raw_today`/`raw_tomorrow`
6. **Energy optimizer** - Processes prices and selects optimal slots
7. **Binary sensors** - Trigger based on current time vs. selected slots
8. **Automations** - Respond to binary sensor states to control inverter

### Services

**`sync_sungrow_parameters`** - Manually refresh Sungrow auto-detected parameters
- Use case: User upgrades inverter or adds battery modules
- Automatically finds config entry with `auto_detected: true`
- Re-runs auto-detection and updates charge/discharge rates
- Called via: `service: battery_energy_trading.sync_sungrow_parameters`

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
```bash
# Check integration structure
ls -la custom_components/battery_energy_trading/

# View integration version
grep version custom_components/battery_energy_trading/manifest.json

# Monitor logs during development
# In Home Assistant: Settings → System → Logs
# Filter by: battery_energy_trading
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
4. **Daily Timeline View** - Consolidated schedule showing all discharge/charge periods for the day
5. **Operation Modes** - Enable/disable switches with inline descriptions
6. **Discharge Schedule** - Aggregate metrics + individual slot details (time, energy, price, revenue)
7. **Charging Schedule** - Aggregate metrics + individual slot details (time, energy, price, cost)
8. **Arbitrage Opportunities** - Top 5 opportunities with full breakdown (charge/discharge windows, profit, ROI)
9. **Price Thresholds** - Configure min/max prices for operations
10. **Battery Settings** - Protection levels and charge/discharge rates
11. **Solar Settings** - Minimum solar power threshold

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

### Running Tests
```bash
pytest tests/                    # Run all tests
pytest tests/ -v                 # Verbose output
pytest tests/test_energy_optimizer.py::TestEnergyOptimizer::test_select_discharge_slots_basic
```

### Coverage
Target: >80% coverage for all modules
- `energy_optimizer.py`: ~95%
- `sungrow_helper.py`: ~90%
- `config_flow.py`: ~85%

See `docs/development/testing.md` for detailed testing documentation.

## Common Troubleshooting

- **Slots not selecting**: Check Nord Pool entity has `raw_today` attribute with price data
- **Battery level not updating**: Verify battery level entity ID is correct and updating
- **Solar override not working**: Check solar power entity reports watts (not kW) and threshold is set appropriately
- **Discharge not triggering**: Verify prices exceed `min_forced_sell_price` threshold and forced discharge switch is ON

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
