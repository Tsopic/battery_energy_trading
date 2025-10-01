# Sungrow Entity Reference for Battery Energy Trading

This document shows the mapping between Battery Energy Trading requirements and actual Sungrow Modbus entities.

## Required Entities

These entities must be configured in Battery Energy Trading's config flow:

### 1. Nord Pool Entity
**Battery Energy Trading expects:** Price sensor with `raw_today` and `raw_tomorrow` attributes

**Sungrow equivalent:** Use your Nord Pool integration sensor (not from Sungrow)
```yaml
Example: sensor.nordpool_kwh_ee_eur_3_10_022
```

### 2. Battery Level Entity
**Battery Energy Trading expects:** Battery state of charge in % (0-100)

**Sungrow entity:** `sensor.battery_level`
- **unique_id:** `sg_battery_level`
- **Address:** 13022 (reg 13023)
- **Unit:** % (0-100%)
- **Note:** This is the actual battery level, includes min/max SoC range

**Alternative:** `sensor.battery_level_nominal`
- **unique_id:** `sg_battery_level_nom`
- **Range:** Between min_soc and max_soc only (e.g., 15-90%)
- **Use if:** You want to work within the configured SoC limits

### 3. Battery Capacity Entity
**Battery Energy Trading expects:** Total battery capacity in kWh

**Sungrow entity:** `sensor.battery_capacity`
- **unique_id:** `sg_battery_capacity`
- **Address:** 5638 (reg 5639)
- **Unit:** kWh
- **Example:** 13.82 kWh (for SBR128 battery)

**Alternatives:**
- `sensor.battery_charge_nominal` - Nominal charge capacity
- `sensor.battery_charge_health_rated` - Health-adjusted capacity
- `sensor.battery_charge` - Current charge in kWh

### 4. Solar Power Entity (Optional)
**Battery Energy Trading expects:** Current solar generation in Watts

**Sungrow entity:** `sensor.total_dc_power`
- **unique_id:** `sg_total_dc_power`
- **Address:** 5016 (reg 5017)
- **Unit:** W
- **Description:** Total DC power from all MPPT strings

**Alternatives:**
- `sensor.mppt1_power` - MPPT1 string power only
- `sensor.mppt2_power` - MPPT2 string power only

### 5. Solar Forecast Entity (Optional - v0.7.0+)
**Battery Energy Trading expects:** Sensor with `wh_hours` attribute containing hourly forecasts

**Sungrow entities:** Not available directly - use Forecast.Solar or Solcast integration

**Recommended:** Install [Forecast.Solar](https://www.home-assistant.io/integrations/forecast_solar/)
```yaml
Example: sensor.energy_production_today
```

## Sungrow Control Entities

These entities are used by Home Assistant automations to control the Sungrow inverter based on Battery Energy Trading binary sensors.

### EMS Mode Control

**Entity:** `select.sungrow_ems_mode` (if using sungrow integration)
**Alternative:** `sensor.ems_mode_selection` (template sensor from modbus)

**Values:**
- `Self-consumption mode (default)` - Normal operation
- `Forced mode` - Manual control of charge/discharge
- `External EMS` - External energy management system

**Related raw sensor:** `sensor.ems_mode_selection_raw`
- **Address:** 13049 (reg 13050)
- **Values:** 0 = Self-consumption, 2 = Forced mode, 3 = External EMS

### Forced Charge/Discharge Command

**Entity:** `sensor.battery_forced_charge_discharge_cmd`

**Values:**
- `Stop (0x33)` - Stop forced operation
- `Charge (0xAA)` - Force battery charging from grid
- `Discharge (0xCC)` - Force battery discharging to grid

**Related raw sensor:** `sensor.battery_forced_charge_discharge_cmd_raw`
- **Address:** 13050 (reg 13051)
- **Values:** 0x33 = Stop, 0xAA = Charge, 0xCC = Discharge

### Forced Charge/Discharge Power

**Entity:** `sensor.battery_forced_charge_discharge_power`

**Purpose:** Sets the power level for forced charging/discharging

**Related input_number:** `input_number.set_sg_forced_charge_discharge_power`
- **Min:** 0 W
- **Max:** 10000 W (adjust for your battery)
- **Step:** 100 W
- **Address:** 13051 (reg 13052)

### Min/Max SoC Control

**Min SoC Entity:** `sensor.min_soc`
- **Address:** 13058 (reg 13059)
- **Range:** 0-50%
- **Purpose:** Prevents battery from discharging below this level

**Max SoC Entity:** `sensor.max_soc`
- **Address:** 13057 (reg 13058)
- **Range:** 50-100%
- **Purpose:** Prevents battery from charging above this level

**Related input_numbers:**
- `input_number.set_sg_min_soc` - Control min SoC (0-50%)
- `input_number.set_sg_max_soc` - Control max SoC (50-100%)

## Example Automation: Forced Discharge

This automation uses Battery Energy Trading's binary sensor to control Sungrow forced discharge:

```yaml
automation:
  - alias: "Battery Trading - Forced Discharge"
    description: "Discharge battery during high price periods detected by Battery Energy Trading"
    triggers:
      - trigger: state
        entity_id: binary_sensor.battery_energy_trading_forced_discharge
    actions:
      - choose:
          # When forced discharge should be active
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_forced_discharge
                state: "on"
            sequence:
              # Set EMS mode to Forced
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13049  # EMS mode selection
                  value: 2  # Forced mode

              # Set forced discharge command
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13050  # Forced charge/discharge cmd
                  value: 0xCC  # Discharge (204 in decimal)

              # Set discharge power (10 kW = 10000 W)
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13051  # Forced power
                  value: 10000  # Use your battery's max discharge rate

          # When forced discharge should stop
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_forced_discharge
                state: "off"
            sequence:
              # Stop forced discharge
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13050  # Forced charge/discharge cmd
                  value: 0x33  # Stop (51 in decimal)

              # Return to self-consumption mode
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13049  # EMS mode selection
                  value: 0  # Self-consumption mode
    mode: single
```

## Example Automation: Forced Charging

This automation charges the battery during cheap price periods:

```yaml
automation:
  - alias: "Battery Trading - Forced Charging"
    description: "Charge battery during low price periods detected by Battery Energy Trading"
    triggers:
      - trigger: state
        entity_id: binary_sensor.battery_energy_trading_cheapest_hours
    conditions:
      # Only charge if forced charging is enabled
      - condition: state
        entity_id: switch.battery_energy_trading_enable_forced_charging
        state: "on"
    actions:
      - choose:
          # When cheap hours active
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_cheapest_hours
                state: "on"
            sequence:
              # Set EMS mode to Forced
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13049
                  value: 2  # Forced mode

              # Set forced charge command
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13050
                  value: 0xAA  # Charge (170 in decimal)

              # Set charge power to 10 kW
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13051
                  value: 10000

          # When cheap hours end
          - conditions:
              - condition: state
                entity_id: binary_sensor.battery_energy_trading_cheapest_hours
                state: "off"
            sequence:
              # Stop forced charging
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13050
                  value: 0x33  # Stop

              # Return to self-consumption
              - action: modbus.write_register
                data:
                  hub: SungrowSHx
                  slave: !secret sungrow_modbus_slave
                  address: 13049
                  value: 0  # Self-consumption
    mode: single
```

## Battery Rate Auto-Detection

Battery Energy Trading can auto-detect charge/discharge rates from your Sungrow inverter model:

**Supported Models:**
- **SH5.0RT / SH5.0RT-20:** 5 kW
- **SH6.0RT / SH6.0RT-20:** 6 kW
- **SH8.0RT / SH8.0RT-20:** 8 kW
- **SH10RT / SH10RT-20:** 10 kW
- **SH3.6RS, SH4.6RS, SH5.0RS, SH6.0RS**

**Detected from entities:**
- `sensor.sungrow_device_type`
- `sensor.inverter_model` (if available)
- Entity ID patterns (e.g., `sensor.sh10rt_*`)

**Manual override:** You can manually set rates in:
- `number.battery_energy_trading_discharge_rate_kw`
- `number.battery_energy_trading_charge_rate_kw`

## Power Flow Sensors

These sensors help understand your energy flow:

**Import/Export:**
- `sensor.import_power` - Power being imported from grid (W)
- `sensor.export_power` - Power being exported to grid (W)
- `sensor.meter_active_power` - Net meter power (negative = export)

**Battery:**
- `sensor.signed_battery_power` - Battery power (positive = charging, negative = discharging)
- `sensor.battery_charging_power` - Charging power only (W)
- `sensor.battery_discharging_power` - Discharging power only (W)

**Load:**
- `sensor.load_power` - Total house load (W)

## Binary Sensors for Status

**Sungrow binary sensors:**
- `binary_sensor.pv_generating` - Solar panels generating power
- `binary_sensor.battery_charging` - Battery is charging
- `binary_sensor.battery_discharging` - Battery is discharging
- `binary_sensor.exporting_power` - Exporting to grid
- `binary_sensor.importing_power` - Importing from grid

**Use these to:**
- Monitor system state
- Create conditional automations
- Display status in dashboards

## Monitoring Energy Flows

**Daily Energy:**
- `sensor.daily_pv_generation` - PV generated today (kWh)
- `sensor.daily_battery_charge` - Battery charged today (kWh)
- `sensor.daily_battery_discharge` - Battery discharged today (kWh)
- `sensor.daily_imported_energy` - Grid imported today (kWh)
- `sensor.daily_exported_energy` - Grid exported today (kWh)

**Total Energy:**
- `sensor.total_pv_generation` - Total PV generated (kWh)
- `sensor.total_battery_charge` - Total battery charged (kWh)
- `sensor.total_battery_discharge` - Total battery discharged (kWh)
- `sensor.total_imported_energy` - Total grid imported (kWh)
- `sensor.total_exported_energy` - Total grid exported (kWh)

## Dashboard Example

See the main dashboard at `/dashboards/battery_energy_trading_dashboard.yaml` which includes:

- Battery Energy Trading sensors and controls
- Sungrow battery level, capacity, and power
- Nord Pool price chart (requires ApexCharts)
- Energy flow visualization

**Replace these with your actual Sungrow entities:**
```yaml
# In the dashboard, replace references to generic entities with:
sensor.battery_level              # Your Sungrow battery level
sensor.battery_capacity           # Your Sungrow battery capacity
sensor.total_dc_power            # Your Sungrow solar power
sensor.nordpool_kwh_ee_eur_3_10_022  # Your Nord Pool sensor
```

## Troubleshooting

**Problem:** Battery doesn't charge/discharge when binary sensor is on

**Solutions:**
1. Check EMS mode is set to "Forced mode" (value 2)
2. Verify forced charge/discharge command is correct (0xAA/0xCC)
3. Check forced power is within your battery's capability
4. Ensure Min/Max SoC allows the operation
5. Check battery level hasn't reached limits

**Problem:** Auto-detection doesn't find Sungrow entities

**Solutions:**
1. Ensure Sungrow Modbus integration is installed and working
2. Check entity IDs match expected patterns (sensor.battery_level, sensor.battery_capacity)
3. Verify entities are available (not "unavailable" or "unknown")
4. Try manual configuration if auto-detection fails

**Problem:** Wrong charge/discharge rates detected

**Solutions:**
1. Manually set rates in Battery Energy Trading number entities
2. Check your inverter model matches supported models
3. Verify `sensor.sungrow_device_type` shows correct model

## Additional Resources

- [Sungrow Modbus Integration](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/)
- [Battery Energy Trading Documentation](https://github.com/Tsopic/battery_energy_trading)
- [Modbus Register Reference](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/blob/main/docs/registers.md)
