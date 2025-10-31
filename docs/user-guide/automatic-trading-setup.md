# Automatic Trading Setup Guide

This guide shows you how to set up fully automatic battery trading with Sungrow inverters using the Battery Energy Trading integration.

## Overview

The integration provides **automation generation** tools that create ready-to-use Home Assistant automations for controlling your Sungrow inverter based on electricity prices. This eliminates manual automation creation while giving you full visibility and control.

## Prerequisites

Before setting up automatic trading, ensure you have:

1. ✅ **Battery Energy Trading integration** installed and configured
2. ✅ **Sungrow integration** installed ([Sungrow-SHx-Inverter-Modbus-Home-Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/))
3. ✅ **Nord Pool integration** providing price data
4. ✅ Basic familiarity with Home Assistant automations

## Step-by-Step Setup

### Step 1: Generate Automation Scripts

The integration provides a service to automatically generate Home Assistant automation YAML for your system.

**Using the Dashboard:**
1. Open your Battery Energy Trading dashboard
2. Find the "🤖 Automation Management" section
3. Click **Generate Automation Scripts**

**Using Developer Tools:**
1. Go to **Developer Tools** → **Services**
2. Select `battery_energy_trading.generate_automation_scripts`
3. Click **Call Service**

**What happens:**
- The integration generates automation YAML tailored to your configuration
- An event is fired: `battery_energy_trading_automation_generated`
- The YAML is stored in `hass.data` for retrieval

### Step 2: Retrieve Generated Automations

The generated automation scripts are stored in Home Assistant's data structure. You can access them via:

**Option A: Listen for Event (Recommended for UI)**
```yaml
# Create an automation to capture the generated scripts
automation:
  - alias: "Battery Trading: Capture Generated Scripts"
    trigger:
      - platform: event
        event_type: battery_energy_trading_automation_generated
    action:
      - service: persistent_notification.create
        data:
          title: "Automation Scripts Generated"
          message: |
            Copy the YAML from the attributes and add to your automations.yaml:
            {{ trigger.event.data.yaml }}
```

**Option B: Developer Tools Template**
```jinja2
{{ states('sensor.battery_energy_trading_automation_status') }}
```

### Step 3: Add Automations to Home Assistant

Copy the generated YAML and add it to your `automations.yaml` file:

**Generated Automation Structure:**
```yaml
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
                    {{ states('number.battery_energy_trading_discharge_rate_kw') | float(5.0) * 1000 }}
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

  - alias: "Battery Trading: Smart Charging Control"
    description: "Auto-generated: Charge battery during low-price slots"
    id: battery_trading_auto_charging
    # ... (similar structure for charging)
```

### Step 4: Reload Automations

After adding the automations to `automations.yaml`:

1. Go to **Developer Tools** → **YAML**
2. Click **Automations** reload button
3. Verify automations appear in **Settings** → **Automations & Scenes**

### Step 5: Enable Features

Control which trading strategies are active using the switches:

**In the Dashboard:**
Navigate to "🎛️ Operation Modes" section and enable:

- ✅ **Enable Discharge at Peak Prices** - Sell battery power during high prices
- ⬜ **Enable Charging at Low Prices** - Buy cheap electricity to charge battery (optional)
- ✅ **Enable Smart Export Control** - Block export during unprofitable periods
- ✅ **Enable Multi-Day Optimization** - Consider tomorrow's prices for better decisions

**Default Configuration:**
The integration ships with safe defaults for solar users:
- **Discharge**: ON (sell excess solar at peak prices)
- **Charging**: OFF (no grid charging by default)
- **Export Management**: ON (prevent unprofitable export)

### Step 6: Monitor Automation Status

Track automation activity in real-time:

**Automation Status Sensor:**
- Entity: `sensor.battery_energy_trading_automation_status`
- Shows: `Active - Discharging`, `Active - Charging`, or `Idle`

**Status Details Card:**
Located in the dashboard "🤖 Automation Status Details" section:
- **Current Status**: Current automation state
- **Last Action**: Last action taken (charge/discharge)
- **Last Action Time**: Timestamp of last action
- **Next Scheduled Action**: Next planned action time
- **Automation Active**: Whether automation is currently active

**Current Status Indicators:**
- 🔴 **Discharging Now** - Battery is selling to grid at high price
- 🟢 **Charging Now** - Battery is buying from grid at low price
- ⚡ **Export Profitable** - Current price makes export profitable
- ☀️ **Solar Active** - Solar generation above threshold

## Understanding the Automation Logic

### Discharge Automation

**Triggers:**
- Binary sensor `forced_discharge` changes state
- Switch `enable_forced_discharge` changes state

**Logic:**
1. Check if `forced_discharge` binary sensor is ON (high price slot)
2. Check if `enable_forced_discharge` switch is ON (user enabled)
3. If both true:
   - Set Sungrow to "Forced Mode"
   - Set discharge power to configured rate (e.g., 5000W)
   - Set charge power to 0
4. If either false:
   - Return to "Self-consumption" mode

### Charging Automation

**Triggers:**
- Binary sensor `cheapest_hours` changes state
- Switch `enable_forced_charging` changes state

**Logic:**
1. Check if `cheapest_hours` binary sensor is ON (low price slot)
2. Check if `enable_forced_charging` switch is ON (user enabled)
3. If both true:
   - Set Sungrow to "Forced Mode"
   - Set charge power to configured rate (e.g., 5000W)
   - Set discharge power to 0
4. If either false:
   - Return to "Self-consumption" mode

## Customizing Automations

### Adjusting Power Rates

The generated automations use dynamic power rates from number entities:

```yaml
value: >
  {{ states('number.battery_energy_trading_discharge_rate_kw') | float(5.0) * 1000 }}
```

**To change rates:**
1. Go to **Number** entities in Home Assistant
2. Adjust `battery_energy_trading_discharge_rate_kw` (default: 5.0 kW)
3. Adjust `battery_energy_trading_charge_rate_kw` (default: 5.0 kW)

Changes take effect immediately—no automation reload needed!

### Adding Notifications

Add notification actions to the automation sequences:

```yaml
sequence:
  - service: select.select_option
    # ... existing Sungrow control

  # Add notification
  - service: notify.mobile_app_your_phone
    data:
      title: "Battery Trading"
      message: "Started discharging at €{{ states('sensor.nordpool_kwh_se3_eur_3_10_025') }}/kWh"
```

### Adding Conditions

Add extra safety conditions:

```yaml
conditions:
  - condition: state
    entity_id: binary_sensor.battery_energy_trading_forced_discharge
    state: 'on'
  - condition: state
    entity_id: switch.battery_energy_trading_enable_forced_discharge
    state: 'on'

  # Add battery level check
  - condition: numeric_state
    entity_id: sensor.sungrow_battery_level
    above: 30
```

## Testing Your Setup

### Dry Run Testing

Before enabling real trading, test the automation logic:

1. **Disable Sungrow Control** (temporarily)
   - Comment out the `select.sungrow_ems_mode` service calls
   - Replace with `persistent_notification.create` for testing

```yaml
action:
  - choose:
      - conditions:
          # ... conditions
        sequence:
          # TESTING: Replace Sungrow control with notification
          - service: persistent_notification.create
            data:
              title: "Battery Trading Test"
              message: "Would start discharging now at {{ now().isoformat() }}"
```

2. **Monitor Binary Sensors**
   - Watch `binary_sensor.battery_energy_trading_forced_discharge`
   - Watch `binary_sensor.battery_energy_trading_cheapest_hours`
   - Verify they trigger at expected price thresholds

3. **Check Automation Status Sensor**
   - Monitor `sensor.battery_energy_trading_automation_status`
   - Verify it updates when binary sensors change

### Live Testing

Once dry run looks good:

1. **Enable One Feature at a Time**
   - Start with discharge only (usually safer for solar users)
   - Monitor for 24 hours
   - Then enable charging if needed

2. **Verify Sungrow Control**
   - Watch `select.sungrow_ems_mode` entity
   - Confirm it switches between "Self-consumption" and "Forced Mode"
   - Check `number.sungrow_forced_discharging_power` updates

3. **Monitor Battery Behavior**
   - Watch battery level during discharge slots
   - Verify discharge rate matches configured value
   - Check battery returns to self-consumption after slot ends

## Troubleshooting

### Automation Not Triggering

**Check 1: Binary Sensors Updating**
```
Developer Tools → States →
binary_sensor.battery_energy_trading_forced_discharge
```
Should toggle between `on`/`off` based on prices.

**Check 2: Switches Enabled**
```
switch.battery_energy_trading_enable_forced_discharge: on
switch.battery_energy_trading_enable_forced_charging: on (if using)
```

**Check 3: Automation Trace**
- Go to **Settings** → **Automations & Scenes**
- Find your Battery Trading automation
- Click **⋮** → **Traces**
- Review last execution

### Sungrow Not Responding

**Check 1: Entity Availability**
```
select.sungrow_ems_mode: available
number.sungrow_forced_discharging_power: available
```

**Check 2: Sungrow Integration**
- Verify Sungrow integration is loaded
- Check for errors in **Settings** → **System** → **Logs**
- Test manual control of `select.sungrow_ems_mode`

**Check 3: Modbus Connection**
- Sungrow integration uses Modbus TCP
- Verify inverter IP address is reachable
- Check inverter firmware supports EMS control

### Wrong Discharge/Charge Times

**Check 1: Price Thresholds**
```
number.battery_energy_trading_min_forced_sell_price: 0.30 EUR
number.battery_energy_trading_max_force_charge_price: 0.00 EUR
```
Adjust to match your local electricity prices.

**Check 2: Hours Configuration**
```
number.battery_energy_trading_forced_discharge_hours: 2
number.battery_energy_trading_force_charging_hours: 1
```
Set to `0` for unlimited hours (discharge all profitable slots).

**Check 3: Nord Pool Data**
- Verify `sensor.nordpool_kwh_*` has `raw_today` attribute
- Check prices are reasonable (not stuck or missing)

### Automation Status Not Updating

**Check 1: Coordinator Tracking**
The automation status sensor requires the coordinator to track actions. This is automatic but verify:

```
sensor.battery_energy_trading_automation_status: <state>
```

If stuck on "Unknown", check Home Assistant logs for coordinator errors.

**Check 2: Force Refresh**
Use the dashboard button or service call:
```
service: battery_energy_trading.force_refresh
```

## Advanced Configuration

### Manual Action Recording

For advanced users implementing custom automations, you can manually record actions in the coordinator:

```yaml
# Custom automation that calls coordinator
automation:
  - alias: "Custom Battery Control"
    trigger:
      - platform: template
        value_template: "{{ custom_logic }}"
    action:
      # Your custom Sungrow control
      - service: select.select_option
        # ...

      # Record action for status tracking
      - service: python_script.record_battery_action
        data:
          action: "discharge"
          next_discharge_slot: "{{ next_slot_time }}"
```

Note: Requires custom python_script implementation.

### Integration with Home Assistant Automations

The generated automations integrate seamlessly with Home Assistant's automation system:

- **Automation Editor**: Edit via UI in Settings → Automations
- **YAML Mode**: Full YAML customization available
- **Automation Traces**: Full execution history and debugging
- **Conditions**: Add time, day, weather conditions
- **Actions**: Extend with notifications, scripts, scenes

## Best Practices

### Solar-First Strategy (Recommended)

For homes with solar panels:

1. ✅ **Enable Discharge** - Sell excess solar at peak prices
2. ⬜ **Disable Charging** - Avoid grid charging, use solar only
3. ✅ **Enable Export Management** - Block export when unprofitable
4. ✅ **Enable Multi-Day Optimization** - Plan around tomorrow's prices

This maximizes solar ROI without increasing grid consumption.

### Grid Trading Strategy

For maximizing arbitrage profits:

1. ✅ **Enable Discharge** - Sell at high prices
2. ✅ **Enable Charging** - Buy at low prices
3. ✅ **Set Appropriate Thresholds**:
   - Discharge price: High enough to cover battery wear
   - Charge price: Low enough for profitable spread
4. ⚡ **Monitor Battery Cycles** - Track long-term battery health

### Safety Limits

Always configure safety limits:

```yaml
number.battery_energy_trading_min_battery_level: 25  # Reserve for blackouts
number.battery_energy_trading_force_charge_target: 70  # Don't overcharge
```

## Monitoring and Analytics

### Track Profitability

Monitor these sensors over time:

- `sensor.battery_energy_trading_discharge_time_slots` (revenue attribute)
- `sensor.battery_energy_trading_charging_time_slots` (cost attribute)
- `sensor.battery_energy_trading_arbitrage_opportunities` (profit estimates)

### Create Performance Dashboard

Add to your dashboard:

```yaml
- type: history-graph
  title: Trading Performance
  entities:
    - sensor.battery_energy_trading_discharge_time_slots
    - sensor.battery_energy_trading_charging_time_slots
    - binary_sensor.battery_energy_trading_forced_discharge
    - binary_sensor.battery_energy_trading_cheapest_hours
  hours_to_show: 48
```

## Support and Resources

- **Integration Docs**: [CLAUDE.md](../../CLAUDE.md)
- **Sungrow Integration Guide**: [docs/integrations/sungrow.md](../integrations/sungrow.md)
- **Dashboard Setup**: [docs/user-guide/dashboard-setup.md](dashboard-setup.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/yourusername/battery_energy_trading/issues)

## Next Steps

Once automatic trading is working:

1. **Monitor for 1 week** - Verify behavior matches expectations
2. **Adjust thresholds** - Fine-tune based on your electricity market
3. **Review profitability** - Calculate actual ROI vs estimates
4. **Expand features** - Add charging, multi-day optimization, etc.

Happy Trading! ⚡🔋💰
