# Manual Testing Guide: Base Entity Refactoring

## Purpose

This guide provides step-by-step instructions for manually verifying the base entity refactoring in a Home Assistant environment.

## Prerequisites

- Home Assistant instance with Battery Energy Trading integration installed
- Nord Pool integration configured
- Battery entities configured (level, capacity)
- Access to Home Assistant Developer Tools

## Test Scenarios

### 1. Verify Sensor Entity State Retrieval

**Test**: `_get_float_state()` works correctly

**Steps**:
1. Navigate to Developer Tools → States
2. Find `sensor.battery_energy_trading_discharge_time_slots`
3. Verify it shows a valid state (not "unknown" or "unavailable")
4. Check attributes contain valid discharge slot data

**Expected**:
- ✅ Sensor displays discharge slots
- ✅ Attributes show energy_kwh, revenue, prices
- ✅ No errors in logs

**Log Check**:
```bash
grep "battery_energy_trading" home-assistant.log | grep -i error
# Should return no errors
```

---

### 2. Verify Number Entity Value Retrieval

**Test**: `_get_number_entity_value()` works correctly

**Steps**:
1. Go to Settings → Devices & Services → Battery Energy Trading
2. Find "Minimum Forced Sell Price" number entity
3. Change value to 0.35 EUR
4. Wait 60 seconds for sensor update
5. Check `sensor.battery_energy_trading_discharge_time_slots` updates

**Expected**:
- ✅ Discharge slots respect new minimum price (0.35 EUR)
- ✅ Only slots >= 0.35 EUR are selected
- ✅ Sensor state updates within 60 seconds

---

### 3. Verify Switch State Detection

**Test**: `_get_switch_state()` works correctly

**Steps**:
1. Find `switch.battery_energy_trading_enable_forced_discharge`
2. Toggle switch OFF
3. Check `binary_sensor.battery_energy_trading_forced_discharge`
4. Verify it shows "off" (not triggering)
5. Toggle switch back ON
6. Verify binary sensor can trigger again

**Expected**:
- ✅ Binary sensor respects switch state
- ✅ When switch OFF → binary sensor stays OFF
- ✅ When switch ON → binary sensor can trigger based on slots

---

### 4. Verify Binary Sensor Functionality

**Test**: Binary sensors still work with inherited helpers

**Steps**:
1. Check all binary sensors are available:
   - `binary_sensor.battery_energy_trading_forced_discharge`
   - `binary_sensor.battery_energy_trading_cheapest_hours`
   - `binary_sensor.battery_energy_trading_battery_low`
   - `binary_sensor.battery_energy_trading_export_profitable`
   - `binary_sensor.battery_energy_trading_low_price`

2. Verify each shows correct state based on current conditions

**Expected**:
- ✅ All binary sensors display valid states (on/off)
- ✅ States change appropriately as conditions change
- ✅ No "unknown" or "unavailable" states

---

### 5. Verify Arbitrage Detection

**Test**: Arbitrage sensor uses configurable efficiency and min profit

**Steps**:
1. Navigate to `sensor.battery_energy_trading_arbitrage_opportunities`
2. Check it shows detected opportunities
3. Change `number.battery_energy_trading_battery_efficiency` to 60%
4. Wait 60 seconds
5. Verify arbitrage opportunities recalculate

**Expected**:
- ✅ Sensor shows arbitrage opportunities
- ✅ Changing efficiency affects detected opportunities
- ✅ Attributes show profit calculations with new efficiency

---

### 6. Verify Error Handling

**Test**: Improved error handling from base_entity.py

**Steps**:
1. Temporarily disable Nord Pool integration
2. Wait 120 seconds
3. Check Battery Energy Trading sensors
4. Review logs for error messages

**Expected**:
- ✅ Sensors show "No data available" or similar
- ✅ Logs show clear warning messages (not crashes)
- ✅ Integration doesn't break
- ✅ Re-enabling Nord Pool restores functionality

---

### 7. Verify Dashboard Integration

**Test**: Dashboard entities still work correctly

**Steps**:
1. Open Battery Energy Trading dashboard
2. Verify all cards display data:
   - Configuration Info
   - Nord Pool Price Chart
   - Current Status
   - Discharge Schedule
   - Charging Schedule
   - Arbitrage Opportunities

3. Interact with number entities and switches
4. Verify changes reflect in sensors within 60 seconds

**Expected**:
- ✅ All dashboard cards load without errors
- ✅ Entity values update when changed
- ✅ Charts render correctly
- ✅ No console errors

---

## Regression Testing

### Critical Paths

1. **Discharge Slot Selection**
   - Verify discharge slots select highest price periods
   - Check battery capacity constraints respected
   - Confirm minimum battery reserve honored

2. **Charging Slot Selection**
   - Verify charging slots select lowest price periods
   - Check target battery level achieved
   - Confirm solar forecast reduces charging need

3. **Switch Control**
   - Enable/disable forced discharge
   - Enable/disable forced charging
   - Enable/disable export management
   - Verify binary sensors respect switch states

4. **Number Entity Configuration**
   - Adjust price thresholds
   - Change battery efficiency
   - Modify discharge/charge hours
   - Verify sensors update correctly

---

## Log Monitoring

### Expected Debug Logs (with improved logging)

```
DEBUG ... Got attribute raw_today from sensor.nordpool_kwh_ee_eur_3_10_022: found
DEBUG ... Switch switch.battery_energy_trading_enable_forced_discharge is on
DEBUG ... Selecting discharge slots: min_price=0.300 EUR/kWh, capacity=12.8 kWh, level=75.0%, rate=5.0 kW
```

### Warning Logs to Watch For

```
WARNING ... Entity sensor.missing_entity not found
WARNING ... Failed to convert state of sensor.invalid to float: could not convert string to float: 'invalid'
```

These are **expected** if entities are misconfigured - the integration should continue working.

### Error Logs (Should NOT Appear)

```
ERROR ... 'NoneType' object has no attribute 'state'  # ❌ Should be handled
ERROR ... KeyError: 'raw_today'  # ❌ Should use safe_get_attribute
ERROR ... AttributeError: ...  # ❌ Should be caught
```

---

## Performance Verification

### Response Time

- Sensor updates: < 1 second after entity state change
- Configuration changes: Reflected within 60 seconds (next update cycle)
- Binary sensor triggers: < 1 second

### Memory Usage

- Check Home Assistant memory usage before/after
- Should show no significant change
- Integration memory footprint should be minimal

---

## Rollback Procedure

If issues are found:

```bash
# 1. Switch back to previous branch
git checkout feat/consecutive-slot-combination

# 2. Restart Home Assistant

# 3. Verify functionality restored
```

---

## Success Criteria

✅ **Pass** - All test scenarios complete successfully
✅ **Pass** - No errors in logs during normal operation
✅ **Pass** - Sensors update correctly when configuration changes
✅ **Pass** - Binary sensors trigger appropriately
✅ **Pass** - Dashboard displays all data correctly
✅ **Pass** - Performance is acceptable (updates within 60s)

❌ **Fail** - Any critical functionality broken
❌ **Fail** - Errors in logs during normal operation
❌ **Fail** - Sensors stuck in "unknown" state
❌ **Fail** - Performance degradation (updates take >120s)

---

## Reporting Issues

If you find any issues during testing:

1. **Capture the error**:
   - Screenshot of Home Assistant UI
   - Relevant log entries
   - Configuration that triggered the issue

2. **Document steps to reproduce**:
   - What were you doing when it occurred?
   - What was the expected vs actual behavior?
   - Can you reproduce it consistently?

3. **Check known limitations**:
   - Review docs/refactoring/consolidate-base-entity-helpers.md
   - Verify it's not a pre-existing issue

4. **Report**:
   - Create GitHub issue with details
   - Tag as "refactoring" and "needs-verification"
   - Include Home Assistant version and integration version
