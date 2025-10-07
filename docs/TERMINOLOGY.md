# Terminology Clarification: Time Slots vs Hours

## Issue

The codebase uses **15-minute time slots** for all operations, but uses "hours" terminology in several places, causing confusion.

## Core Concept

**The system operates on 15-minute time slots, NOT hourly slots.**

- Nord Pool provides prices in 15-minute intervals (96 slots/day)
- All discharge/charge decisions are made per 15-minute slot
- Battery calculations use 15-minute slot duration (0.25 hours)

## Terminology Guide

### ✅ CORRECT Usage of "Hours"

These refer to **maximum duration limits**:

| Entity | Meaning | Example |
|--------|---------|---------|
| `number.forced_discharge_hours` | **Maximum hours** to discharge (across all slots) | `2` = discharge for up to 2 hours total |
| `number.force_charging_hours` | **Maximum hours** to charge (across all slots) | `1` = charge for up to 1 hour total |
| `max_hours` parameter | Duration limit for slot selection | `max_hours=2` = select slots totaling ≤ 2 hours |

**Example:**
- `forced_discharge_hours = 2` with 15-min slots
- System selects up to **8 slots** (8 × 15min = 2 hours)
- Special case: `0` = unlimited (use battery capacity as limit)

### ❌ CONFUSING Usage (Should Be "Slots")

These entity names incorrectly suggest hourly operation:

| Current Name | What It Actually Does | Better Name |
|--------------|----------------------|-------------|
| `DischargeHoursSensor` | Selects 15-min **discharge slots** | `DischorgeSlotsSensor` or `DischargeTimeSlotsSensor` |
| `ChargingHoursSensor` | Selects 15-min **charging slots** | `ChargingSlotsSensor` or `ChargingTimeSlotsSensor` |
| `CheapestHoursSensor` | Detects if current **15-min slot** is cheap | `CheapestSlotsSensor` or `ChargingSlotActive` |
| `SENSOR_DISCHARGE_HOURS` | Constant for discharge **slots** sensor | `SENSOR_DISCHARGE_SLOTS` |
| `SENSOR_CHARGING_HOURS` | Constant for charging **slots** sensor | `SENSOR_CHARGING_SLOTS` |

**Note:** These are already deployed entity names, so changing them would be a **breaking change**. See recommendations below.

## Code Examples

### Energy Per Slot Calculation

```python
# Calculate slot duration (15 minutes = 0.25 hours)
slot_duration_hours = self._calculate_slot_duration(raw_prices)  # Returns 0.25
energy_per_slot = discharge_rate_kw * slot_duration_hours
# Example: 10kW × 0.25h = 2.5 kWh per 15-min slot
```

### Max Hours to Max Slots Conversion

```python
# User sets: forced_discharge_hours = 2 (hours)
# System converts to slot count:
max_slots = int(max_hours / slot_duration_hours)
# Example: 2 hours / 0.25 = 8 slots
```

### Slot Selection Output

```python
{
    "start": datetime(2025, 10, 2, 17, 0),  # 17:00
    "end": datetime(2025, 10, 2, 17, 15),   # 17:15 (15-minute slot!)
    "duration_hours": 0.25,  # 15 minutes in hours
    "energy_kwh": 2.5,       # Energy for this 15-min slot
    "price": 0.45,           # EUR/kWh for this slot
    "revenue": 1.125         # 2.5 kWh × 0.45 EUR
}
```

## User-Facing Clarity

### Current UI

**Confusing names** but correct behavior:

```yaml
- entity: sensor.battery_energy_trading_discharge_hours
  name: "Discharge Time Slots"  # ✅ Name clarifies it's slots

- entity: number.battery_energy_trading_forced_discharge_hours
  name: "Forced Discharge Hours"  # ✅ Correctly means duration limit
```

### Dashboard Display

**Sensor state** shows 15-min slots clearly:

```
State: "17:00-17:15 (2.5kWh @€0.45), 17:15-17:30 (2.5kWh @€0.46), ..."
```

Attributes show:
```json
{
  "slot_count": 8,
  "total_energy_kwh": 20.0,
  "slots": [
    {
      "start": "2025-10-02T17:00:00",
      "end": "2025-10-02T17:15:00",   // ← 15-minute intervals!
      "energy_kwh": 2.5,
      "price": 0.45
    },
    ...
  ]
}
```

## Documentation Updates Needed

### ✅ Already Clear

These docs correctly explain 15-minute operation:

- `CLAUDE.md` - States "15-minute slot support"
- `README.md` - Mentions "15-minute intervals"
- `energy_optimizer.py` docstrings - Use "slot" terminology

### ⚠️ Needs Clarification

Files that reference "hours" without explaining slots:

1. **`TESTING_IMPLEMENTATION_SUMMARY.md`**
   - References "CheapestHoursSensor" without explaining it's 15-min slots
   - Should add note: "Despite 'hours' in name, operates on 15-minute slots"

2. **`CLAUDE.md`**
   - Section "15-Minute Slot Support" exists ✅
   - Should add to "Common Troubleshooting" section

3. **Entity descriptions in `number.py`**
   - `"Forced Discharge Hours"` - Should add description text explaining it's duration limit across 15-min slots

4. **Test files**
   - Test class names use "Hours" (e.g., `TestCheapestHoursSensor`)
   - Tests are correct, just naming is legacy

## Recommendations

### Short-Term (No Breaking Changes)

1. **Add clarifying descriptions** to number entities:
   ```python
   BatteryTradingNumber(
       entry,
       NUMBER_FORCED_DISCHARGE_HOURS,
       "Forced Discharge Duration",  # ← Clearer
       0, 24, 1,
       DEFAULT_FORCED_DISCHARGE_HOURS,
       "hours",
       "mdi:clock-outline",
       description="Maximum hours to discharge across 15-minute slots"  # ← NEW
   )
   ```

2. **Update sensor friendly names** to emphasize "slots":
   ```python
   self._attr_name = "Discharge Time Slots"  # ✅ Already done!
   self._attr_name = "Charging Time Slots"   # ✅ Already done!
   self._attr_name = "Cheapest Slots"        # ← Should change from "Cheapest Hours"
   ```

3. **Add doc comments** clarifying slot vs hour distinction:
   ```python
   class DischargeHoursSensor(BatteryTradingSensor):
       """Sensor for discharge time slots.

       Despite the entity ID containing 'hours', this sensor operates on
       15-minute time slots from Nord Pool pricing data. The max_hours
       parameter controls the total duration across all selected slots.
       """
   ```

4. **Update documentation** with explicit slot explanations

### Long-Term (Major Version)

Consider renaming entities in v2.0:

```python
# Old (confusing)
SENSOR_DISCHARGE_HOURS = "discharge_hours"
BINARY_SENSOR_CHEAPEST_HOURS = "cheapest_hours"

# New (clear)
SENSOR_DISCHARGE_SLOTS = "discharge_slots"
BINARY_SENSOR_CHEAPEST_SLOTS = "cheapest_slots"
```

**Migration guide** would be needed for users.

## Summary

**Key Points:**

✅ The system correctly operates on 15-minute slots
✅ Calculations are correct (slot_duration_hours = 0.25)
✅ User-facing sensor states clearly show 15-min intervals

⚠️ Entity names use "hours" terminology (legacy from before 15-min support)
⚠️ `max_hours` parameters mean "total duration limit" not "hourly operation"
⚠️ Some documentation needs clarification

**No code bugs** - just terminology that could be clearer!

**Immediate action:** Update docs and entity descriptions to clarify slot-based operation.
