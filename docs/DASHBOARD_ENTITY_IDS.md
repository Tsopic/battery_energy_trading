# Dashboard Entity ID Reference

## ✅ Entity IDs Are Now Fixed (v0.8.1+)

Starting with version 0.8.1, all entities use `suggested_object_id` to ensure consistent, predictable entity IDs across all installations.

## Finding Your Entity IDs

The Battery Energy Trading integration now creates entities with fixed IDs that match the dashboard expectations:

### Method 1: Using Developer Tools (Recommended)

1. Go to **Developer Tools** → **States**
2. Filter by `battery_energy_trading`
3. You'll see all entities created by the integration

### Method 2: Check Configuration Sensor

The integration provides a diagnostic sensor that shows your configured entities:

1. Look for: `sensor.battery_energy_trading_configuration`
2. Click on it to see attributes with your actual entity IDs

## Expected Entity IDs

Based on the dashboard, here are the entities that should exist:

### Sensors
- `sensor.battery_energy_trading_configuration` - Configuration info
- `sensor.battery_energy_trading_discharge_time_slots` - Discharge schedule
- `sensor.battery_energy_trading_charging_time_slots` - Charging schedule
- `sensor.battery_energy_trading_arbitrage_opportunities` - Arbitrage opportunities

### Binary Sensors
- `binary_sensor.battery_energy_trading_forced_discharge` - Currently discharging
- `binary_sensor.battery_energy_trading_cheapest_hours` - Currently charging
- `binary_sensor.battery_energy_trading_export_profitable` - Export is profitable
- `binary_sensor.battery_energy_trading_solar_available` - Solar available
- `binary_sensor.battery_energy_trading_battery_low` - Battery low

### Switches
- `switch.battery_energy_trading_enable_forced_charging` - Enable charging
- `switch.battery_energy_trading_enable_forced_discharge` - Enable discharge
- `switch.battery_energy_trading_enable_export_management` - Enable export control
- `switch.battery_energy_trading_enable_multiday_optimization` - Enable multi-day optimization

### Number Entities
- `number.battery_energy_trading_forced_discharge_hours` - Discharge hours limit
- `number.battery_energy_trading_min_export_price` - Min export price
- `number.battery_energy_trading_min_forced_sell_price` - Min sell price
- `number.battery_energy_trading_max_force_charge_price` - Max charge price
- `number.battery_energy_trading_force_charging_hours` - Charging hours limit
- `number.battery_energy_trading_force_charge_target` - Charge target %
- `number.battery_energy_trading_min_battery_level` - Min battery level %
- `number.battery_energy_trading_min_solar_threshold` - Min solar threshold W
- `number.battery_energy_trading_discharge_rate_kw` - Discharge rate kW
- `number.battery_energy_trading_charge_rate_kw` - Charge rate kW

## Troubleshooting "Entity not found"

If you see "Entity not found" errors in the dashboard:

1. **Check integration is loaded**: Settings → Devices & Services → Battery Energy Trading should show "1 device"
2. **Verify entity IDs**: Go to Developer Tools → States and search for `battery_energy_trading`
3. **Check for entry_id in entity IDs**: If entities have format like `sensor.battery_energy_trading_abc123_configuration`, you have a config entry ID in the entity name
4. **Reload integration**: Settings → Devices & Services → Battery Energy Trading → ⋮ → Reload
5. **Check logs**: Settings → System → Logs, filter by `battery_energy_trading`

## Entity ID Format (v0.8.1+)

With `suggested_object_id` set, Home Assistant creates predictable entity IDs as:
```
{platform}.{suggested_object_id}
```

For this integration, the pattern is:
```python
suggested_object_id = f"battery_energy_trading_{entity_type}"
```

Examples:
- Configuration sensor: `sensor.battery_energy_trading_configuration`
- Forced discharge: `binary_sensor.battery_energy_trading_forced_discharge`
- Discharge rate: `number.battery_energy_trading_discharge_rate_kw`

If you have multiple instances, Home Assistant will add suffixes like `_2`, `_3` to prevent conflicts.

## Migration from v0.8.0 or Earlier

If you're upgrading from v0.8.0 or earlier:

1. **Entity IDs changed**: Old format was `sensor.battery_energy_trading_{entry_id}_{type}`
2. **Dashboard will work automatically**: The new entity IDs match the dashboard expectations
3. **Manual cleanup may be needed**: Old entities may need to be deleted from Settings → Devices & Services → Battery Energy Trading → Device
4. **Automations need updating**: If you created automations referencing old entity IDs, update them to the new format
