# Sungrow Inverter Integration Guide

This guide helps you integrate Battery Energy Trading with the [Sungrow SHx Inverter Modbus integration](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/).

## 🔌 Prerequisites

1. **Sungrow Modbus Integration** installed and working
2. **Nord Pool Integration** installed and configured
3. **Battery Energy Trading** integration installed

## 📋 Entity Mapping

### Required Entities from Sungrow Integration

The Sungrow integration provides these entities (adjust names based on your setup):

| Sungrow Entity | Battery Trading Config | Description |
|----------------|----------------------|-------------|
| `sensor.sungrow_battery_level` | Battery Level Entity | Battery SOC (%) |
| `sensor.sungrow_battery_capacity` | Battery Capacity Entity | Total capacity (kWh) |
| `sensor.sungrow_pv_power` | Solar Power Entity | Current PV production (W) |

### Common Sungrow Entity Names

```yaml
# Battery Level (State of Charge)
sensor.sungrow_battery_level
sensor.sh10rt_battery_level
sensor.battery_soc

# Battery Capacity
sensor.sungrow_battery_capacity
sensor.sh10rt_battery_capacity
# Note: Often need to create template sensor (see below)

# Solar Power
sensor.sungrow_pv_power
sensor.sungrow_total_pv_power
sensor.sh10rt_pv_power
```

## ⚙️ Configuration Steps

### Step 1: Find Your Sungrow Entities

1. Go to **Developer Tools** → **States**
2. Filter by "sungrow" or "battery"
3. Note down the exact entity IDs

### Step 2: Configure Battery Energy Trading

When setting up the integration:

1. **Nord Pool Entity**: Your Nord Pool price sensor
   ```
   sensor.nordpool_kwh_ee_eur_3_10_022
   ```

2. **Battery Level Entity**: Sungrow SOC sensor
   ```
   sensor.sungrow_battery_level
   ```

3. **Battery Capacity Entity**: Total battery capacity
   ```
   sensor.sungrow_battery_capacity
   ```

4. **Solar Power Entity** (Optional): PV production
   ```
   sensor.sungrow_pv_power
   ```

### Step 3: Create Battery Capacity Sensor (If Needed)

If your Sungrow integration doesn't provide a capacity sensor:

```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Sungrow Battery Capacity"
        unique_id: sungrow_battery_capacity
        unit_of_measurement: "kWh"
        device_class: energy
        state: >
          {% if is_state('sensor.sungrow_device_type_code', '247') %}
            13.0
          {% elif is_state('sensor.sungrow_device_type_code', '387') %}
            25.6
          {% else %}
            10.0
          {% endif %}
```

**Common Sungrow Battery Capacities:**
- SBR064: 6.4 kWh
- SBR096: 9.6 kWh
- SBR128: 12.8 kWh
- SBR160: 16.0 kWh
- SBR192: 19.2 kWh
- SBR224: 22.4 kWh
- SBR256: 25.6 kWh

### Step 4: Configure Charge/Discharge Rates

Set these based on your inverter model:

| Model | Max Charge | Max Discharge |
|-------|------------|---------------|
| SH5.0RT | 5.0 kW | 5.0 kW |
| SH6.0RT | 6.0 kW | 6.0 kW |
| SH8.0RT | 8.0 kW | 8.0 kW |
| SH10RT | 10.0 kW | 10.0 kW |

In the integration:
1. Go to **Settings** → **Devices & Services** → **Battery Energy Trading**
2. Set **Battery Discharge Rate** to your inverter's max (e.g., 5.0 kW)
3. Set **Battery Charge Rate** to your inverter's max (e.g., 5.0 kW)

## 🔄 Automation Examples

### Control Sungrow Charging Based on Price

```yaml
automation:
  - alias: "Sungrow: Enable Charging at Cheap Prices"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_cheapest_hours
        to: 'on'
    condition:
      - condition: state
        entity_id: switch.battery_energy_trading_enable_forced_charging
        state: 'on'
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.sungrow_charge_battery_from_grid

  - alias: "Sungrow: Disable Charging After Cheap Period"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_cheapest_hours
        to: 'off'
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.sungrow_charge_battery_from_grid
```

### Force Discharge at Peak Prices

```yaml
automation:
  - alias: "Sungrow: Force Discharge at Peak Prices"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
        to: 'on'
    condition:
      - condition: state
        entity_id: switch.battery_energy_trading_enable_forced_discharge
        state: 'on'
    action:
      - service: number.set_value
        target:
          entity_id: number.sungrow_battery_forced_charge_discharge_power
        data:
          value: -5000  # Negative = discharge (W)

  - alias: "Sungrow: Stop Force Discharge"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
        to: 'off'
    action:
      - service: number.set_value
        target:
          entity_id: number.sungrow_battery_forced_charge_discharge_power
        data:
          value: 0  # Return to self-consumption
```

### Manage Export Limits

```yaml
automation:
  - alias: "Sungrow: Control Export Based on Price"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_export_profitable
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_export_profitable
                state: 'on'
            sequence:
              - service: number.set_value
                target:
                  entity_id: number.sungrow_export_power_limit
                data:
                  value: 10000  # Allow full export
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_export_profitable
                state: 'off'
            sequence:
              - service: number.set_value
                target:
                  entity_id: number.sungrow_export_power_limit
                data:
                  value: 0  # Block export
```

## 📊 Dashboard Integration

Add Sungrow entities to your Battery Energy Trading dashboard:

```yaml
# Add to your dashboard
- type: entities
  title: "Sungrow Inverter Status"
  entities:
    - entity: sensor.sungrow_battery_level
      name: "Battery Level"
    - entity: sensor.sungrow_pv_power
      name: "Solar Production"
    - entity: sensor.sungrow_battery_power
      name: "Battery Power"
    - entity: sensor.sungrow_load_power
      name: "Home Consumption"
    - entity: sensor.sungrow_export_power
      name: "Grid Export"
```

## 🔍 Troubleshooting

### Battery Level Not Updating

Check if the Sungrow sensor is updating:
```yaml
# Developer Tools → Template
{{ states('sensor.sungrow_battery_level') }}
{{ state_attr('sensor.sungrow_battery_level', 'unit_of_measurement') }}
```

### Capacity Sensor Missing

Create a helper:
1. **Settings** → **Devices & Services** → **Helpers**
2. **+ CREATE HELPER** → **Number**
3. Name: "Battery Capacity"
4. Min: 0, Max: 30, Step: 0.1
5. Unit: kWh
6. Set your battery capacity

### Solar Power Not Detected

Verify the threshold:
```yaml
# The default is 500W
# Adjust if needed:
number.battery_energy_trading_min_solar_threshold
```

## 🎯 Recommended Settings for Sungrow

### For Solar-Only Operation (Default)
- ✅ Enable Forced Discharge
- ❌ Disable Forced Charging
- ✅ Enable Export Management
- **Min Sell Price**: 0.30 EUR/kWh
- **Min Battery Level**: 25%
- **Solar Threshold**: 500 W

### For Grid Trading
- ✅ Enable Forced Discharge
- ✅ Enable Forced Charging
- ✅ Enable Export Management
- **Max Buy Price**: 0.00 EUR/kWh (or your threshold)
- **Charge Target**: 70%

## 📱 Example Complete Configuration

```yaml
# configuration.yaml

# Nord Pool Integration
sensor:
  - platform: nordpool
    region: "EE"
    currency: "EUR"

# Sungrow Battery Capacity Helper
template:
  - sensor:
      - name: "Sungrow Battery Capacity"
        unique_id: sungrow_battery_capacity
        unit_of_measurement: "kWh"
        device_class: energy
        state: "12.8"  # Your battery capacity

# Automations for Sungrow Control
automation:
  # Charging automation
  - alias: "Battery Trading: Control Sungrow Charging"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_cheapest_hours
    action:
      - service: "switch.turn_{{ trigger.to_state.state }}"
        target:
          entity_id: switch.sungrow_charge_battery_from_grid

  # Discharge automation
  - alias: "Battery Trading: Control Sungrow Discharge"
    trigger:
      - platform: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
    action:
      - service: number.set_value
        target:
          entity_id: number.sungrow_battery_forced_charge_discharge_power
        data:
          value: >
            {% if trigger.to_state.state == 'on' %}
              -5000
            {% else %}
              0
            {% endif %}
```

## 💡 Tips

1. **Start Conservative**: Begin with discharge enabled, charging disabled
2. **Monitor First Week**: Watch how it performs before enabling charging
3. **Adjust Thresholds**: Fine-tune prices based on your electricity rates
4. **Check Logs**: Look for errors in Home Assistant logs
5. **Test Manually**: Use developer tools to test services before automating

## 🆘 Support

- **Sungrow Integration**: https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues
- **Battery Energy Trading**: https://github.com/Tsopic/battery_energy_trading/issues
- **Community**: https://community.home-assistant.io/
