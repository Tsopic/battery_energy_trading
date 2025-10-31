# Automatic Energy Trading Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable fully automatic energy trading with Sungrow inverters while providing complete observability and user control over all trading functions.

**Architecture:** Add automation platform with script generation, enhance dashboard with automation status cards, create service calls for Sungrow control, and ensure all parameters are exposed and documented consistently.

**Tech Stack:** Home Assistant automation platform, Jinja2 templating, YAML script generation, coordinator pattern for state management

---

## Current State Analysis

### ✅ What Works
- **Entities**: All 13 number entities, 4 switches, 6 binary sensors, 3 sensors exist and function
- **Dashboard**: 100% attribute coverage, automatic entity detection via configuration sensor
- **Optimization**: EnergyOptimizer selects optimal charge/discharge slots with 15-min granularity
- **Sungrow Auto-Detection**: Automatic entity mapping and charge/discharge rate detection

### ❌ Gaps Identified

1. **No Automation Platform**
   - Users must manually create YAML automations
   - No built-in automation scripts or blueprints
   - Documentation shows examples but no automatic generation

2. **Dashboard Limitations**
   - Missing: Real-time automation status indicators
   - Missing: Active trading mode display
   - Missing: Last action timestamp and next scheduled action
   - Missing: Quick enable/disable automation buttons

3. **Service Call Interface**
   - No service calls for Sungrow control (users create automations manually)
   - No "test automation" service for validation
   - No "force refresh" service for immediate re-calculation

4. **Observability Gaps**
   - No history of executed actions (charge/discharge start/stop times)
   - No revenue/cost tracking over time (only estimates)
   - No alert system for failed automation triggers
   - No diagnostic sensor for automation health

---

## Implementation Tasks

### Task 1: Create Automation Script Generator Platform

**Files:**
- Create: `custom_components/battery_energy_trading/automation_helper.py`
- Create: `custom_components/battery_energy_trading/services.yaml`
- Modify: `custom_components/battery_energy_trading/__init__.py:159-191`
- Test: `tests/test_automation_helper.py`

**Step 1: Write failing test for automation script generation**

```python
# tests/test_automation_helper.py
import pytest
from custom_components.battery_energy_trading.automation_helper import AutomationScriptGenerator

@pytest.mark.asyncio
async def test_generate_sungrow_discharge_automation():
    """Test generating Sungrow discharge control automation."""
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.sungrow_battery_level",
        discharge_rate_entity="number.battery_energy_trading_discharge_rate_kw"
    )

    automation_yaml = generator.generate_discharge_automation()

    assert "automation:" in automation_yaml
    assert "binary_sensor.battery_energy_trading_forced_discharge" in automation_yaml
    assert "select.sungrow_ems_mode" in automation_yaml
    assert "number.sungrow_forced_discharging_power" in automation_yaml
    assert "Forced Mode" in automation_yaml

@pytest.mark.asyncio
async def test_generate_charging_automation():
    """Test generating charging control automation."""
    generator = AutomationScriptGenerator(
        nordpool_entity="sensor.nordpool_kwh_se3_eur_3_10_025",
        battery_level_entity="sensor.sungrow_battery_level",
        charge_rate_entity="number.battery_energy_trading_charge_rate_kw"
    )

    automation_yaml = generator.generate_charging_automation()

    assert "binary_sensor.battery_energy_trading_cheapest_hours" in automation_yaml
    assert "number.sungrow_forced_charging_power" in automation_yaml
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_automation_helper.py::test_generate_sungrow_discharge_automation -v`
Expected: FAIL with "No module named 'automation_helper'"

**Step 3: Write minimal AutomationScriptGenerator class**

```python
# custom_components/battery_energy_trading/automation_helper.py
"""Automation script generation helpers."""

from __future__ import annotations
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

DISCHARGE_AUTOMATION_TEMPLATE = """
automation:
  - alias: "Battery Trading: Smart Discharge Control"
    description: "Auto-generated: Discharge battery during high-price slots"
    id: battery_trading_auto_discharge
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
      - platform: state
        entity_id: switch.battery_energy_trading_enable_forced_discharge
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_forced_discharge
                state: 'on'
              - condition: state
                entity_id: switch.battery_energy_trading_enable_forced_discharge
                state: 'on'
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.sungrow_ems_mode
                data:
                  option: "Forced Mode"
              - service: number.set_value
                target:
                  entity_id: number.sungrow_forced_discharging_power
                data:
                  value: >
                    {{{{ states('{discharge_rate_entity}') | float(5.0) * 1000 }}}}
              - service: number.set_value
                target:
                  entity_id: number.sungrow_forced_charging_power
                data:
                  value: 0
        default:
          - service: select.select_option
            target:
              entity_id: select.sungrow_ems_mode
            data:
              option: "Self-consumption"
"""

CHARGING_AUTOMATION_TEMPLATE = """
automation:
  - alias: "Battery Trading: Smart Charging Control"
    description: "Auto-generated: Charge battery during low-price slots"
    id: battery_trading_auto_charging
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_cheapest_hours
      - platform: state
        entity_id: switch.battery_energy_trading_enable_forced_charging
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_cheapest_hours
                state: 'on'
              - condition: state
                entity_id: switch.battery_energy_trading_enable_forced_charging
                state: 'on'
            sequence:
              - service: select.select_option
                target:
                  entity_id: select.sungrow_ems_mode
                data:
                  option: "Forced Mode"
              - service: number.set_value
                target:
                  entity_id: number.sungrow_forced_charging_power
                data:
                  value: >
                    {{{{ states('{charge_rate_entity}') | float(5.0) * 1000 }}}}
              - service: number.set_value
                target:
                  entity_id: number.sungrow_forced_discharging_power
                data:
                  value: 0
        default:
          - service: select.select_option
            target:
              entity_id: select.sungrow_ems_mode
            data:
              option: "Self-consumption"
"""


class AutomationScriptGenerator:
    """Generate Home Assistant automation scripts for battery trading."""

    def __init__(
        self,
        nordpool_entity: str,
        battery_level_entity: str,
        discharge_rate_entity: str | None = None,
        charge_rate_entity: str | None = None,
    ) -> None:
        """Initialize generator with entity IDs."""
        self.nordpool_entity = nordpool_entity
        self.battery_level_entity = battery_level_entity
        self.discharge_rate_entity = discharge_rate_entity or "number.battery_energy_trading_discharge_rate_kw"
        self.charge_rate_entity = charge_rate_entity or "number.battery_energy_trading_charge_rate_kw"

    def generate_discharge_automation(self) -> str:
        """Generate discharge automation YAML."""
        return DISCHARGE_AUTOMATION_TEMPLATE.format(
            discharge_rate_entity=self.discharge_rate_entity
        )

    def generate_charging_automation(self) -> str:
        """Generate charging automation YAML."""
        return CHARGING_AUTOMATION_TEMPLATE.format(
            charge_rate_entity=self.charge_rate_entity
        )

    def generate_all_automations(self) -> str:
        """Generate all automation scripts."""
        return f"""# Battery Energy Trading - Auto-Generated Automations
# Generated for Nord Pool: {self.nordpool_entity}
# Battery Level: {self.battery_level_entity}

{self.generate_discharge_automation()}

{self.generate_charging_automation()}
"""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_automation_helper.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add custom_components/battery_energy_trading/automation_helper.py tests/test_automation_helper.py
git commit -m "feat: add automation script generator for Sungrow control"
```

---

### Task 2: Add Service Calls for Automation Management

**Files:**
- Create: `custom_components/battery_energy_trading/services.yaml`
- Modify: `custom_components/battery_energy_trading/__init__.py:159-191`
- Test: `tests/test_init.py:test_service_registration`

**Step 1: Write failing test for service registration**

```python
# Add to tests/test_init.py
@pytest.mark.asyncio
async def test_service_generate_automation_scripts(hass, mock_coordinator):
    """Test generate_automation_scripts service."""
    with patch("custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator"):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NORDPOOL_ENTITY: "sensor.nordpool",
                CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
                CONF_BATTERY_CAPACITY_ENTITY: "sensor.battery_capacity",
            },
        )
        entry.add_to_hass(hass)
        await async_setup_entry(hass, entry)

    # Verify service is registered
    assert hass.services.has_service(DOMAIN, "generate_automation_scripts")

    # Call service
    await hass.services.async_call(
        DOMAIN,
        "generate_automation_scripts",
        {"config_entry_id": entry.entry_id},
        blocking=True,
    )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_init.py::test_service_generate_automation_scripts -v`
Expected: FAIL with "Service not registered"

**Step 3: Add service registration to __init__.py**

```python
# Modify custom_components/battery_energy_trading/__init__.py

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery Energy Trading from a config entry."""
    # ... existing coordinator setup code ...

    # Register services
    async def handle_generate_automation_scripts(call: ServiceCall) -> None:
        """Handle generate_automation_scripts service call."""
        from .automation_helper import AutomationScriptGenerator

        config_entry_id = call.data.get("config_entry_id", entry.entry_id)
        target_entry = hass.config_entries.async_get_entry(config_entry_id)

        if not target_entry:
            _LOGGER.error("Config entry %s not found", config_entry_id)
            return

        generator = AutomationScriptGenerator(
            nordpool_entity=target_entry.data[CONF_NORDPOOL_ENTITY],
            battery_level_entity=target_entry.data[CONF_BATTERY_LEVEL_ENTITY],
        )

        automation_yaml = generator.generate_all_automations()

        # Store in hass.data for retrieval
        hass.data[DOMAIN][f"{config_entry_id}_automations"] = automation_yaml

        _LOGGER.info("Generated automation scripts for entry %s", config_entry_id)

        # Fire event for UI notification
        hass.bus.async_fire(
            f"{DOMAIN}_automation_generated",
            {"config_entry_id": config_entry_id, "yaml": automation_yaml},
        )

    async def handle_force_refresh(call: ServiceCall) -> None:
        """Handle force_refresh service call."""
        config_entry_id = call.data.get("config_entry_id", entry.entry_id)
        coordinator = hass.data[DOMAIN][config_entry_id]
        await coordinator.async_request_refresh()
        _LOGGER.info("Forced coordinator refresh for entry %s", config_entry_id)

    # Register services on first setup
    if not hass.services.has_service(DOMAIN, "generate_automation_scripts"):
        hass.services.async_register(
            DOMAIN,
            "generate_automation_scripts",
            handle_generate_automation_scripts,
        )

    if not hass.services.has_service(DOMAIN, "force_refresh"):
        hass.services.async_register(
            DOMAIN,
            "force_refresh",
            handle_force_refresh,
        )

    return True
```

**Step 4: Create services.yaml**

```yaml
# custom_components/battery_energy_trading/services.yaml
generate_automation_scripts:
  name: Generate Automation Scripts
  description: Generate Home Assistant automation scripts for Sungrow inverter control
  fields:
    config_entry_id:
      name: Config Entry ID
      description: Configuration entry ID (optional, uses default if not specified)
      required: false
      selector:
        text:

force_refresh:
  name: Force Refresh
  description: Force immediate re-calculation of charge/discharge slots
  fields:
    config_entry_id:
      name: Config Entry ID
      description: Configuration entry ID (optional, uses default if not specified)
      required: false
      selector:
        text:
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_init.py::test_service_generate_automation_scripts -v`
Expected: PASS

**Step 6: Commit**

```bash
git add custom_components/battery_energy_trading/__init__.py custom_components/battery_energy_trading/services.yaml tests/test_init.py
git commit -m "feat: add generate_automation_scripts and force_refresh services"
```

---

### Task 3: Add Automation Status Sensors

**Files:**
- Modify: `custom_components/battery_energy_trading/sensor.py:1-50`
- Modify: `custom_components/battery_energy_trading/const.py:40-48`
- Test: `tests/test_sensor.py`

**Step 1: Write failing test for automation status sensor**

```python
# Add to tests/test_sensor.py
@pytest.mark.asyncio
async def test_automation_status_sensor(mock_coordinator, mock_hass, mock_config_entry):
    """Test automation status sensor."""
    sensor = AutomationStatusSensor(mock_coordinator, mock_config_entry)

    # Mock last action data
    mock_coordinator.data = {
        "last_action": "discharge",
        "last_action_time": "2025-10-31T14:30:00",
        "next_discharge_slot": "2025-10-31T16:00:00",
        "automation_active": True,
    }

    assert sensor.native_value == "Active - Discharging"
    assert sensor.extra_state_attributes["last_action"] == "discharge"
    assert sensor.extra_state_attributes["last_action_time"] == "2025-10-31T14:30:00"
    assert sensor.extra_state_attributes["next_scheduled_action"] == "2025-10-31T16:00:00"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sensor.py::test_automation_status_sensor -v`
Expected: FAIL with "AutomationStatusSensor not defined"

**Step 3: Add SENSOR_AUTOMATION_STATUS constant**

```python
# Modify custom_components/battery_energy_trading/const.py
# Add to sensor types section:
SENSOR_AUTOMATION_STATUS: Final = "automation_status"
SENSOR_LAST_ACTION: Final = "last_action"
```

**Step 4: Implement AutomationStatusSensor class**

```python
# Add to custom_components/battery_energy_trading/sensor.py after existing sensor classes

class AutomationStatusSensor(BatteryEnergyTradingBaseEntity, SensorEntity):
    """Sensor showing current automation status."""

    def __init__(
        self,
        coordinator: BatteryEnergyTradingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Automation Status"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{SENSOR_AUTOMATION_STATUS}"
        self._attr_icon = "mdi:robot"

    @property
    def native_value(self) -> str:
        """Return automation status."""
        data = self.coordinator.data

        if not data:
            return "Unknown"

        automation_active = data.get("automation_active", False)
        if not automation_active:
            return "Inactive"

        last_action = data.get("last_action", "none")

        if last_action == "discharge":
            return "Active - Discharging"
        elif last_action == "charge":
            return "Active - Charging"
        elif last_action == "idle":
            return "Active - Idle"
        else:
            return "Active"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self.coordinator.data
        if not data:
            return {}

        return {
            "last_action": data.get("last_action", "none"),
            "last_action_time": data.get("last_action_time", "unknown"),
            "next_scheduled_action": data.get("next_discharge_slot") or data.get("next_charge_slot"),
            "automation_health": data.get("automation_health", "unknown"),
        }
```

**Step 5: Register new sensor in async_setup_entry**

```python
# Modify async_setup_entry in sensor.py to add AutomationStatusSensor
sensors.append(AutomationStatusSensor(coordinator, entry))
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_sensor.py::test_automation_status_sensor -v`
Expected: PASS

**Step 7: Commit**

```bash
git add custom_components/battery_energy_trading/sensor.py custom_components/battery_energy_trading/const.py tests/test_sensor.py
git commit -m "feat: add automation status sensor for observability"
```

---

### Task 4: Enhance Dashboard with Automation Status Cards

**Files:**
- Modify: `dashboards/battery_energy_trading_dashboard.yaml:24-50`

**Step 1: Review current dashboard structure**

Review: `dashboards/battery_energy_trading_dashboard.yaml`
Identify: Location for new automation status section (after Configuration Info card)

**Step 2: Add automation status card**

```yaml
# Add after Configuration Info Card (line ~50)

  # Automation Status Card
  - type: entities
    title: "🤖 Automation Status"
    entities:
      - entity: sensor.battery_energy_trading_automation_status
        name: Status
      - type: attribute
        entity: sensor.battery_energy_trading_automation_status
        attribute: last_action
        name: Last Action
      - type: attribute
        entity: sensor.battery_energy_trading_automation_status
        attribute: last_action_time
        name: Last Action Time
      - type: attribute
        entity: sensor.battery_energy_trading_automation_status
        attribute: next_scheduled_action
        name: Next Scheduled
      - type: button
        name: Generate Automation Scripts
        action_name: Generate
        tap_action:
          action: call-service
          service: battery_energy_trading.generate_automation_scripts
      - type: button
        name: Force Refresh Calculations
        action_name: Refresh
        tap_action:
          action: call-service
          service: battery_energy_trading.force_refresh
```

**Step 3: Test dashboard rendering**

Test: Open Home Assistant dashboard editor, import updated YAML
Expected: New "Automation Status" card displays with Generate/Refresh buttons

**Step 4: Commit**

```bash
git add dashboards/battery_energy_trading_dashboard.yaml
git commit -m "feat: add automation status card to dashboard"
```

---

### Task 5: Create Documentation for Automatic Trading Setup

**Files:**
- Create: `docs/user-guide/automatic-trading-setup.md`
- Modify: `docs/integrations/sungrow.md:133-200`
- Modify: `docs/README.md`

**Step 1: Write automatic trading setup guide**

```markdown
# docs/user-guide/automatic-trading-setup.md

# Automatic Energy Trading Setup Guide

This guide walks you through setting up fully automatic battery trading with your Sungrow inverter.

## Prerequisites

- ✅ Battery Energy Trading integration installed and configured
- ✅ Nord Pool integration working
- ✅ Sungrow integration installed
- ✅ Battery level, capacity, and solar power entities mapped

## Quick Setup (Automated)

### Step 1: Generate Automation Scripts

1. Open the Battery Energy Trading dashboard
2. Locate the "🤖 Automation Status" card
3. Click **Generate Automation Scripts** button
4. The service will create automations based on your configuration

### Step 2: Review Generated Automations

The service generates two main automations:

**Smart Discharge Control:**
- Triggers: When `binary_sensor.battery_energy_trading_forced_discharge` turns ON
- Action: Sets Sungrow to Forced Mode and begins discharging at configured rate
- Triggers: When binary sensor turns OFF
- Action: Returns Sungrow to Self-consumption mode

**Smart Charging Control:**
- Triggers: When `binary_sensor.battery_energy_trading_cheapest_hours` turns ON
- Action: Sets Sungrow to Forced Mode and begins charging at configured rate
- Triggers: When binary sensor turns OFF
- Action: Returns Sungrow to Self-consumption mode

### Step 3: Copy Automations to configuration.yaml

1. Check Home Assistant logs for the generated YAML
2. Alternatively, use Developer Tools → Events and listen for `battery_energy_trading_automation_generated`
3. Copy the YAML to your `automations.yaml` file
4. Reload automations: Settings → Automations → ⋮ → Reload automations

### Step 4: Enable Trading Functions

In the Battery Energy Trading dashboard:

1. **Enable Forced Discharge** (switch ON) - Allows selling during high prices
2. **Enable Forced Charging** (switch OFF by default) - Enable only if you want grid charging
3. **Enable Export Management** (switch ON) - Manages when to export to grid

## Manual Setup (Advanced Users)

If you prefer to create automations manually, see the [Sungrow Integration Guide](../integrations/sungrow.md) for complete YAML examples.

## Observability

### Dashboard Monitoring

The dashboard provides real-time visibility:

- **Automation Status Sensor**: Shows if automation is active, last action, next scheduled action
- **Binary Sensors**: Show when discharge/charge conditions are met
- **Time Slot Sensors**: Show selected slots with revenue/cost estimates

### Checking Automation Health

1. Monitor `sensor.battery_energy_trading_automation_status`
2. Check `last_action_time` attribute to ensure recent activity
3. Verify `automation_health` attribute is "healthy"

## Troubleshooting

### Automation Not Triggering

**Check:**
1. Switches are enabled (`switch.battery_energy_trading_enable_forced_discharge`)
2. Price thresholds are reasonable (`number.battery_energy_trading_min_forced_sell_price`)
3. Battery level is above minimum (`number.battery_energy_trading_min_battery_level`)

**Debug:**
1. Use **Force Refresh** button to recalculate slots immediately
2. Check `sensor.battery_energy_trading_discharge_time_slots` attributes for selected slots
3. Enable debug logging: `logger: custom_components.battery_energy_trading: debug`

### Sungrow Not Responding

**Verify:**
1. `select.sungrow_ems_mode` entity exists and is controllable
2. `number.sungrow_forced_discharging_power` can be set manually
3. Check Sungrow integration logs for communication errors

## Safety Features

The integration includes multiple safety layers:

1. **Minimum Battery Level**: Never discharges below configured threshold
2. **Battery Low Warning**: `binary_sensor.battery_energy_trading_battery_low` alerts at 15%
3. **Solar Priority**: Discharge only occurs if solar is insufficient
4. **Manual Override**: Disable switches immediately stops automation

## Customization

### Adjust Price Thresholds

- `number.battery_energy_trading_min_forced_sell_price`: Minimum price for discharge (default 0.30 EUR)
- `number.battery_energy_trading_max_force_charge_price`: Maximum price for charging (default 0.00 EUR)

### Adjust Duration Limits

- `number.battery_energy_trading_forced_discharge_hours`: Max discharge duration across all slots (default 2h)
- `number.battery_energy_trading_force_charging_hours`: Max charge duration (default 1h)

### Adjust Battery Protection

- `number.battery_energy_trading_min_battery_level`: Never discharge below this (default 25%)
- `number.battery_energy_trading_battery_low_threshold`: Warning threshold (default 15%)

## Next Steps

- Review [Dashboard Entity Reference](dashboard-entity-reference.md) for all available parameters
- Check [Sungrow Integration Guide](../integrations/sungrow.md) for advanced automation examples
- Monitor your first day of automatic trading via the dashboard
```

**Step 2: Update Sungrow integration guide**

Modify `docs/integrations/sungrow.md` to reference the new automatic setup:

```markdown
# Add at line 133, before "Complete Automation Examples"

## 🚀 Quick Automatic Setup

**New in v0.15.0+:** Use the automatic setup wizard instead of manually creating automations.

See [Automatic Trading Setup Guide](../user-guide/automatic-trading-setup.md) for:
- One-click automation script generation
- Automatic Sungrow entity detection
- Built-in observability and health monitoring

## 🔄 Manual Automation Examples (Advanced)

For users who prefer full control over automation logic:
```

**Step 3: Update main docs README**

Add entry to `docs/README.md`:

```markdown
### User Guides
- [Automatic Trading Setup](user-guide/automatic-trading-setup.md) - **NEW**: One-click automation generation
- [Dashboard Setup](user-guide/dashboard-setup.md)
- [Dashboard Entity Reference](user-guide/dashboard-entity-reference.md)
```

**Step 4: Commit**

```bash
git add docs/user-guide/automatic-trading-setup.md docs/integrations/sungrow.md docs/README.md
git commit -m "docs: add automatic trading setup guide with automation generation"
```

---

### Task 6: Update Dashboard Entity Reference

**Files:**
- Modify: `docs/user-guide/dashboard-entity-reference.md`

**Step 1: Add new entities to reference**

Add to entity tables in `docs/user-guide/dashboard-entity-reference.md`:

```markdown
### Automation Status Sensors

| Entity ID | Description | Attributes |
|-----------|-------------|------------|
| `sensor.battery_energy_trading_automation_status` | Current automation status | `last_action`, `last_action_time`, `next_scheduled_action`, `automation_health` |

#### Automation Status States

- **Active - Discharging**: Currently in discharge mode
- **Active - Charging**: Currently in charging mode
- **Active - Idle**: Automation enabled but no action scheduled
- **Inactive**: Automation switches are off

### Services

| Service | Description | Parameters |
|---------|-------------|------------|
| `battery_energy_trading.generate_automation_scripts` | Generate YAML automations for Sungrow control | `config_entry_id` (optional) |
| `battery_energy_trading.force_refresh` | Force immediate recalculation of charge/discharge slots | `config_entry_id` (optional) |
```

**Step 2: Commit**

```bash
git add docs/user-guide/dashboard-entity-reference.md
git commit -m "docs: document new automation status sensor and services"
```

---

### Task 7: Add Coordinator Tracking for Last Actions

**Files:**
- Modify: `custom_components/battery_energy_trading/coordinator.py:40-80`
- Test: `tests/test_coordinator.py`

**Step 1: Write failing test for action tracking**

```python
# Add to tests/test_coordinator.py
@pytest.mark.asyncio
async def test_coordinator_tracks_last_action(hass, mock_api):
    """Test coordinator tracks last discharge/charge actions."""
    coordinator = BatteryEnergyTradingCoordinator(hass, "sensor.nordpool")
    coordinator.data = {"raw_today": [{"start": "2025-10-31T14:00:00", "value": 0.35}]}

    # Simulate discharge action
    coordinator.record_action("discharge", "2025-10-31T14:30:00")

    assert coordinator.data["last_action"] == "discharge"
    assert coordinator.data["last_action_time"] == "2025-10-31T14:30:00"
    assert coordinator.data["automation_active"] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_coordinator.py::test_coordinator_tracks_last_action -v`
Expected: FAIL with "method record_action not found"

**Step 3: Add action tracking to coordinator**

```python
# Modify custom_components/battery_energy_trading/coordinator.py

class BatteryEnergyTradingCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage Battery Energy Trading data."""

    def __init__(self, hass: HomeAssistant, nordpool_entity: str) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.nordpool_entity = nordpool_entity
        self._last_action: str = "none"
        self._last_action_time: str = "never"
        self._automation_active: bool = False

    def record_action(self, action: str, timestamp: str) -> None:
        """Record an automation action."""
        self._last_action = action
        self._last_action_time = timestamp
        self._automation_active = True

        # Update coordinator data
        if self.data:
            self.data["last_action"] = action
            self.data["last_action_time"] = timestamp
            self.data["automation_active"] = True
            self.async_update_listeners()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Nord Pool."""
        # ... existing code ...

        # Include action tracking in data
        result = {
            "raw_today": raw_today,
            "raw_tomorrow": raw_tomorrow,
            "current_price": current_price,
            "last_action": self._last_action,
            "last_action_time": self._last_action_time,
            "automation_active": self._automation_active,
        }

        return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_coordinator.py::test_coordinator_tracks_last_action -v`
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/battery_energy_trading/coordinator.py tests/test_coordinator.py
git commit -m "feat: add action tracking to coordinator for automation observability"
```

---

### Task 8: Integration Testing - End-to-End Automation Flow

**Files:**
- Create: `tests/test_integration_automation.py`

**Step 1: Write integration test**

```python
# tests/test_integration_automation.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.battery_energy_trading import async_setup_entry
from custom_components.battery_energy_trading.const import DOMAIN, CONF_NORDPOOL_ENTITY, CONF_BATTERY_LEVEL_ENTITY, CONF_BATTERY_CAPACITY_ENTITY

@pytest.mark.asyncio
async def test_full_automation_flow(hass: HomeAssistant):
    """Test complete automation flow from setup to action tracking."""

    # Setup integration
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test",
        data={
            CONF_NORDPOOL_ENTITY: "sensor.nordpool",
            CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
            CONF_BATTERY_CAPACITY_ENTITY: "sensor.battery_capacity",
        },
        source="user",
    )

    with patch("custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator"):
        await async_setup_entry(hass, entry)

    # Verify services registered
    assert hass.services.has_service(DOMAIN, "generate_automation_scripts")
    assert hass.services.has_service(DOMAIN, "force_refresh")

    # Call generate_automation_scripts
    await hass.services.async_call(
        DOMAIN,
        "generate_automation_scripts",
        {},
        blocking=True,
    )

    # Verify automation scripts generated
    assert f"{entry.entry_id}_automations" in hass.data[DOMAIN]
    automation_yaml = hass.data[DOMAIN][f"{entry.entry_id}_automations"]
    assert "binary_sensor.battery_energy_trading_forced_discharge" in automation_yaml

    # Simulate coordinator action tracking
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.record_action("discharge", "2025-10-31T14:30:00")

    # Verify action tracked in coordinator data
    assert coordinator.data["last_action"] == "discharge"
    assert coordinator.data["automation_active"] is True
```

**Step 2: Run integration test**

Run: `pytest tests/test_integration_automation.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_integration_automation.py
git commit -m "test: add integration test for end-to-end automation flow"
```

---

### Task 9: Update CHANGELOG and Version

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `custom_components/battery_energy_trading/manifest.json`

**Step 1: Update CHANGELOG**

```markdown
# Add to CHANGELOG.md

## [0.15.0] - 2025-10-31

### Added
- **Automatic Trading**: One-click automation script generation for Sungrow inverters
- **Automation Status Sensor**: Real-time visibility into automation state and last actions
- **Service Calls**: `generate_automation_scripts` and `force_refresh` services
- **Dashboard Enhancements**: Automation status card with Generate/Refresh buttons
- **Action Tracking**: Coordinator now tracks last action, timestamp, and automation health
- **Comprehensive Documentation**: Automatic trading setup guide with troubleshooting

### Improved
- **Observability**: Full visibility into automation execution and next scheduled actions
- **User Control**: All trading functions have clear enable/disable toggles
- **Dashboard Consistency**: All entities and parameters now documented and accessible
```

**Step 2: Update manifest.json**

```json
{
  "domain": "battery_energy_trading",
  "name": "Battery Energy Trading",
  "version": "0.15.0",
  ...
}
```

**Step 3: Commit**

```bash
git add CHANGELOG.md custom_components/battery_energy_trading/manifest.json
git commit -m "chore: bump version to 0.15.0 with automatic trading features"
```

---

## Testing Checklist

After completing all tasks, verify:

- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] Integration test passes: `pytest tests/test_integration_automation.py -v`
- [ ] Coverage remains >90%: `pytest --cov=custom_components.battery_energy_trading --cov-report=term`
- [ ] Dashboard loads without errors in Home Assistant
- [ ] Service calls work in Developer Tools → Services
- [ ] Automation status sensor updates in real-time
- [ ] Generated automation YAML is valid and complete
- [ ] Documentation is accurate and links work

## Deployment Steps

1. Run all tests and verify coverage
2. Build and test in local Home Assistant instance
3. Create git tag: `git tag -a v0.15.0 -m "Release v0.15.0: Automatic Trading"`
4. Push to GitHub: `git push origin v0.15.0`
5. Update HACS repository
6. Announce release with feature highlights

## Post-Release Validation

Monitor first 24 hours for:
- User feedback on automation generation
- Dashboard rendering issues
- Service call errors in logs
- Coordinator action tracking accuracy

---

## Architecture Decision Records

### ADR-001: Why Automation Script Generation Instead of Built-in Scripts?

**Decision:** Generate YAML automations via service call rather than include them as built-in scripts.

**Rationale:**
- Users can review and customize generated automations before deployment
- Fits Home Assistant's configuration-as-code philosophy
- Allows advanced users to modify automation logic
- Easier debugging (users can see exact automation in UI)

**Alternative Considered:** Blueprint system - rejected due to complexity and limited flexibility for per-inverter customization.

### ADR-002: Why Coordinator-Based Action Tracking?

**Decision:** Store last action, timestamp, and automation state in coordinator data.

**Rationale:**
- Coordinator is single source of truth for all integration data
- Automatic propagation to all entities via CoordinatorEntity pattern
- No additional state storage needed
- Fits existing DataUpdateCoordinator architecture

**Alternative Considered:** Separate state storage in hass.data - rejected due to coordination complexity and potential state desync.

---

## Success Metrics

**Completion Criteria:**
- ✅ Zero manual automation setup required for basic Sungrow trading
- ✅ All trading parameters exposed and documented in dashboard
- ✅ Real-time visibility into automation state and actions
- ✅ One-click automation generation and refresh
- ✅ Comprehensive troubleshooting documentation

**User Experience Goals:**
- Setup time: < 5 minutes from integration install to automatic trading
- Observability: User always knows what automation is doing and why
- Control: Clear enable/disable for all trading functions
- Confidence: Dashboard shows estimates before actions execute
