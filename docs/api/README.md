# API Documentation

Technical reference for Battery Energy Trading integration classes, methods, and entities.

## Core Modules

### Energy Optimizer

**Module**: `custom_components.battery_energy_trading.energy_optimizer`

The `EnergyOptimizer` class provides core optimization algorithms:

- `select_discharge_slots()` - Select highest-price slots for battery discharge
- `select_charging_slots()` - Select cheapest slots for grid charging
- `calculate_arbitrage_opportunities()` - Find profitable charge/discharge cycles
- `is_current_slot_selected()` - Check if current time is in selected slots

**Documentation**: Coming soon

### Sungrow Helper

**Module**: `custom_components.battery_energy_trading.sungrow_helper`

The `SungrowHelper` class provides automatic Sungrow inverter detection:

- `is_sungrow_integration_available()` - Check if Sungrow entities exist
- `detect_sungrow_entities()` - Auto-detect battery and solar entities
- `detect_inverter_model_from_entities()` - Identify inverter model
- `async_get_auto_configuration()` - Return complete auto-detected config

**Documentation**: Coming soon

### Configuration Flow

**Module**: `custom_components.battery_energy_trading.config_flow`

Handles integration setup and configuration:

- `async_step_user()` - Initial setup step
- `async_step_sungrow_auto()` - Automatic Sungrow configuration
- `async_step_manual()` - Manual entity selection
- `async_step_dashboard()` - Dashboard setup wizard

**Documentation**: Coming soon

## Entity Platforms

### Sensors

**Module**: `custom_components.battery_energy_trading.sensor`

Sensor entities:
- `ConfigurationSensor` - Exposes configured entity IDs
- `DischargeTimeSlotsSensor` - Selected discharge schedule
- `ChargingTimeSlotsSensor` - Selected charging schedule
- `ArbitrageOpportunitiesSensor` - Detected arbitrage opportunities

**Documentation**: Coming soon

### Binary Sensors

**Module**: `custom_components.battery_energy_trading.binary_sensor`

Binary sensor entities:
- `ForcedDischargeSensor` - Currently in high-price discharge slot
- `CheapestHoursSensor` - Currently in cheap charging slot
- `LowPriceSensor` - Price below export threshold
- `ExportProfitableSensor` - Export is currently profitable
- `BatteryLowSensor` - Battery below threshold
- `SolarAvailableSensor` - Solar production above threshold

**Documentation**: Coming soon

### Number Entities

**Module**: `custom_components.battery_energy_trading.number`

Configuration number entities for prices, thresholds, hours, and rates.

**Documentation**: Coming soon

### Switch Entities

**Module**: `custom_components.battery_energy_trading.switch`

Control switch entities:
- `EnableForcedChargingSwitch` - Enable/disable grid charging
- `EnableForcedDischargeSwitch` - Enable/disable forced discharge
- `EnableExportManagementSwitch` - Enable/disable export control
- `EnableMultidayOptimizationSwitch` - Enable/disable multi-day optimization

**Documentation**: Coming soon

## Services

### `sync_sungrow_parameters`

Manually refresh Sungrow auto-detected parameters.

**Service**: `battery_energy_trading.sync_sungrow_parameters`

**Use Case**: User upgrades inverter or adds battery modules

**Documentation**: Coming soon

## Base Classes

### BatteryEnergyTradingBaseEntity

**Module**: `custom_components.battery_energy_trading.base_entity`

Base class for all entities providing:
- Coordinator access
- Device info
- Common helpers

**Documentation**: Coming soon

## Constants

**Module**: `custom_components.battery_energy_trading.const`

Integration constants, defaults, and configuration keys.

**Documentation**: Coming soon

---

## Documentation Status

This section is under development. Detailed API documentation will be added for:

- Class signatures and parameters
- Method return types
- Usage examples
- Integration patterns

For now, refer to:
- **[CLAUDE.md](../../CLAUDE.md)** - Architecture overview and key concepts
- **[Source Code](../../custom_components/battery_energy_trading/)** - Well-commented implementation
- **[Development Guide](../development/README.md)** - Development workflow

## Contributing

API documentation contributions welcome! Please follow:
- Google-style Python docstrings
- Type hints for all parameters and return values
- Usage examples
- See existing code for style reference
