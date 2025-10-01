# Dashboard Completeness Audit

**Date:** October 1, 2025
**Branch:** `refactor/dashboard-completeness-review`
**Status:** In Progress

## Executive Summary

Comprehensive audit of all controllable attributes in Battery Energy Trading integration vs. dashboard representation. Identifies missing attributes, particularly detailed time slot information that should be exposed to users.

## Methodology

1. **Entity Analysis**: Read all entity platform files (number.py, switch.py, sensor.py, binary_sensor.py)
2. **Attribute Extraction**: Identified all `extra_state_attributes` exposed by sensors
3. **Dashboard Comparison**: Compared against current dashboard YAML configuration
4. **Gap Analysis**: Documented missing controllable attributes and display options

## Entity Inventory

### Number Entities (10 total)

All number entities are **FULLY REPRESENTED** in the dashboard:

| Entity | Dashboard Section | Status |
|--------|------------------|--------|
| `number.battery_energy_trading_forced_discharge_hours` | Discharge Settings | ✅ Present |
| `number.battery_energy_trading_min_export_price` | Price Thresholds | ✅ Present |
| `number.battery_energy_trading_min_forced_sell_price` | Price Thresholds | ✅ Present |
| `number.battery_energy_trading_max_force_charge_price` | Price Thresholds | ✅ Present |
| `number.battery_energy_trading_force_charging_hours` | Charging Settings | ✅ Present |
| `number.battery_energy_trading_force_charge_target` | Charging Settings | ✅ Present |
| `number.battery_energy_trading_min_battery_level` | Battery Settings | ✅ Present |
| `number.battery_energy_trading_min_solar_threshold` | Solar Settings | ✅ Present |
| `number.battery_energy_trading_discharge_rate_kw` | Battery Settings | ✅ Present |
| `number.battery_energy_trading_charge_rate_kw` | Battery Settings | ✅ Present |

### Switch Entities (4 total)

All switch entities are **FULLY REPRESENTED** in the dashboard:

| Entity | Dashboard Section | Status |
|--------|------------------|--------|
| `switch.battery_energy_trading_enable_forced_charging` | Operation Modes | ✅ Present |
| `switch.battery_energy_trading_enable_forced_discharge` | Operation Modes | ✅ Present |
| `switch.battery_energy_trading_enable_export_management` | Operation Modes | ✅ Present |
| `switch.battery_energy_trading_enable_multiday_optimization` | Operation Modes | ✅ Present |

### Binary Sensor Entities (6 total)

All binary sensors are **FULLY REPRESENTED** in the dashboard:

| Entity | Dashboard Section | Status |
|--------|------------------|--------|
| `binary_sensor.battery_energy_trading_forced_discharge` | Current Status | ✅ Present |
| `binary_sensor.battery_energy_trading_cheapest_hours` | Current Status | ✅ Present |
| `binary_sensor.battery_energy_trading_export_profitable` | Current Status | ✅ Present |
| `binary_sensor.battery_energy_trading_solar_available` | Current Status | ✅ Present |
| `binary_sensor.battery_energy_trading_battery_low` | Battery Monitoring | ✅ Present |
| `binary_sensor.battery_energy_trading_low_price` | Battery Monitoring | ✅ Present |

### Sensor Entities (3 total)

Main sensors are present, but **DETAILED SLOT ATTRIBUTES ARE MISSING**:

| Entity | Dashboard Section | Status |
|--------|------------------|--------|
| `sensor.battery_energy_trading_discharge_time_slots` | Discharge Schedule | ⚠️ Partial |
| `sensor.battery_energy_trading_charging_time_slots` | Charging Schedule | ⚠️ Partial |
| `sensor.battery_energy_trading_arbitrage_opportunities` | Arbitrage | ⚠️ Minimal |

## Missing Attributes - Critical Findings

### 1. Discharge Time Slots - Missing Detailed Slot Information

**Currently in Dashboard:**
- ✅ `slot_count` - Total number of discharge slots
- ✅ `total_energy_kwh` - Total energy to be discharged
- ✅ `estimated_revenue_eur` - Estimated revenue
- ✅ `average_price` - Average price across all slots

**Missing from Dashboard:**
- ❌ `slots` array - Individual slot details with:
  - `start` - ISO datetime of slot start
  - `end` - ISO datetime of slot end
  - `energy_kwh` - Energy for this specific slot
  - `price` - Price for this slot
  - `revenue` - Revenue for this slot

**Impact**: Users cannot see **when** each discharge slot occurs or the **price per slot**. They only see aggregate data.

**Code Reference** (sensor.py:278-288):
```python
"slots": [
    {
        "start": s["start"].isoformat(),
        "end": s["end"].isoformat(),
        "energy_kwh": s["energy_kwh"],
        "price": s["price"],
        "revenue": s["revenue"],
    }
    for s in slots
],
```

### 2. Charging Time Slots - Missing Detailed Slot Information

**Currently in Dashboard:**
- ✅ `slot_count` - Total number of charging slots
- ✅ `total_energy_kwh` - Total energy to charge
- ✅ `estimated_cost_eur` - Estimated cost
- ✅ `average_price` - Average price across all slots

**Missing from Dashboard:**
- ❌ `slots` array - Individual slot details with:
  - `start` - ISO datetime of slot start
  - `end` - ISO datetime of slot end
  - `energy_kwh` - Energy for this specific slot
  - `price` - Price for this slot
  - `cost` - Cost for this slot

**Impact**: Users cannot see **when** each charging slot occurs or the **price per slot**. They only see aggregate data.

**Code Reference** (sensor.py:405-414):
```python
"slots": [
    {
        "start": s["start"].isoformat(),
        "end": s["end"].isoformat(),
        "energy_kwh": s["energy_kwh"],
        "price": s["price"],
        "cost": s["cost"],
    }
    for s in slots
],
```

### 3. Arbitrage Opportunities - Missing Detailed Information

**Currently in Dashboard:**
- ✅ Main state shows best opportunity text

**Missing from Dashboard:**
- ❌ `opportunities_count` - Total opportunities found
- ❌ `best_profit` - Best profit amount
- ❌ `best_roi` - Best ROI percentage
- ❌ `all_opportunities` - Top 5 opportunities array with:
  - `charge_start` - When to start charging
  - `charge_end` - When to stop charging
  - `discharge_start` - When to discharge
  - `discharge_end` - When to stop discharging
  - `charge_price` - Price to charge at
  - `discharge_price` - Price to discharge at
  - `profit` - Profit amount
  - `roi_percent` - ROI percentage
  - `energy_kwh` - Energy amount

**Impact**: Users cannot see all arbitrage opportunities, only the best one in text form. No structured data to build automations or charts.

**Code Reference** (sensor.py:203-208):
```python
return {
    "opportunities_count": len(opportunities),
    "best_profit": opportunities[0]["profit"] if opportunities else 0,
    "best_roi": opportunities[0]["roi_percent"] if opportunities else 0,
    "all_opportunities": opportunities[:5],  # Top 5
}
```

### 4. Switch Entity Attributes - Missing Context

**Available Attributes** (switch.py:107-112):
```python
@property
def extra_state_attributes(self) -> dict[str, Any]:
    return {
        "description": self._description,
        "switch_type": self._switch_type,
    }
```

**Currently in Dashboard:**
- ✅ Switch entities are shown

**Missing from Dashboard:**
- ❌ `description` attribute - Helpful context for each switch
- ❌ `switch_type` attribute - Technical identifier

**Impact**: Users don't see helpful descriptions explaining what each switch does directly in the UI.

## Recommendations

### Priority 1: Display Individual Time Slots

**Problem**: Users cannot see the specific times when charging/discharging will occur.

**Solution**: Add detailed slot displays for both charging and discharging schedules.

**Implementation**:
```yaml
# For Discharge Schedule
- type: markdown
  content: |
    ### Discharge Slots Detail
    {% for slot in state_attr('sensor.battery_energy_trading_discharge_time_slots', 'slots') %}
    - **{{ as_timestamp(slot.start) | timestamp_custom('%H:%M') }} - {{ as_timestamp(slot.end) | timestamp_custom('%H:%M') }}**: {{ slot.energy_kwh | round(1) }} kWh @ €{{ slot.price | round(3) }}/kWh (Revenue: €{{ slot.revenue | round(2) }})
    {% endfor %}

# For Charging Schedule
- type: markdown
  content: |
    ### Charging Slots Detail
    {% for slot in state_attr('sensor.battery_energy_trading_charging_time_slots', 'slots') %}
    - **{{ as_timestamp(slot.start) | timestamp_custom('%H:%M') }} - {{ as_timestamp(slot.end) | timestamp_custom('%H:%M') }}**: {{ slot.energy_kwh | round(1) }} kWh @ €{{ slot.price | round(3) }}/kWh (Cost: €{{ slot.cost | round(2) }})
    {% endfor %}
```

### Priority 2: Expand Arbitrage Opportunities Display

**Problem**: Only one arbitrage opportunity is shown as text.

**Solution**: Display all top opportunities with full details.

**Implementation**:
```yaml
# Add attributes to arbitrage card
- type: entities
  title: "💰 Arbitrage Opportunities Detail"
  entities:
    - type: attribute
      entity: sensor.battery_energy_trading_arbitrage_opportunities
      attribute: opportunities_count
      name: "Total Opportunities"
    - type: attribute
      entity: sensor.battery_energy_trading_arbitrage_opportunities
      attribute: best_profit
      name: "Best Profit"
      suffix: " EUR"
    - type: attribute
      entity: sensor.battery_energy_trading_arbitrage_opportunities
      attribute: best_roi
      name: "Best ROI"
      suffix: " %"

# Add markdown for detailed opportunities
- type: markdown
  content: |
    ### Top Arbitrage Opportunities
    {% for opp in state_attr('sensor.battery_energy_trading_arbitrage_opportunities', 'all_opportunities') %}
    - **Charge**: {{ opp.charge_start }} - {{ opp.charge_end }} @ €{{ opp.charge_price | round(3) }}
    - **Discharge**: {{ opp.discharge_start }} - {{ opp.discharge_end }} @ €{{ opp.discharge_price | round(3) }}
    - **Profit**: €{{ opp.profit | round(2) }} (ROI: {{ opp.roi_percent | round(1) }}%)
    ---
    {% endfor %}
```

### Priority 3: Add Switch Descriptions

**Problem**: Switch purpose isn't immediately clear without hovering.

**Solution**: Display switch descriptions in the dashboard.

**Implementation**:
```yaml
# Enhanced switch display with descriptions
- type: entities
  title: "Enable/Disable Features"
  entities:
    - entity: switch.battery_energy_trading_enable_forced_discharge
      name: "Enable Discharge at Peak Prices"
      secondary_info: attribute
      attribute: description
    - entity: switch.battery_energy_trading_enable_forced_charging
      name: "Enable Charging at Low Prices"
      secondary_info: attribute
      attribute: description
    - entity: switch.battery_energy_trading_enable_export_management
      name: "Enable Smart Export Control"
      secondary_info: attribute
      attribute: description
    - entity: switch.battery_energy_trading_enable_multiday_optimization
      name: "Enable Multi-Day Optimization"
      secondary_info: attribute
      attribute: description
```

### Priority 4: Visual Time Slot Timeline

**Problem**: Time slots are hard to visualize without a timeline view.

**Solution**: Add a timeline card showing when slots occur throughout the day.

**Implementation** (requires custom card or ApexCharts):
```yaml
# Timeline visualization using markdown with emoji indicators
- type: markdown
  content: |
    ## 📅 Today's Schedule Timeline

    ### Discharge Periods (🔴)
    {% for slot in state_attr('sensor.battery_energy_trading_discharge_time_slots', 'slots') %}
    🔴 {{ as_timestamp(slot.start) | timestamp_custom('%H:%M') }} - {{ as_timestamp(slot.end) | timestamp_custom('%H:%M') }} | {{ slot.energy_kwh | round(1) }} kWh @ €{{ slot.price | round(3) }}
    {% endfor %}

    ### Charging Periods (🟢)
    {% for slot in state_attr('sensor.battery_energy_trading_charging_time_slots', 'slots') %}
    🟢 {{ as_timestamp(slot.start) | timestamp_custom('%H:%M') }} - {{ as_timestamp(slot.end) | timestamp_custom('%H:%M') }} | {{ slot.energy_kwh | round(1) }} kWh @ €{{ slot.price | round(3) }}
    {% endfor %}
```

## Additional Findings

### Good Practices Already in Place

1. ✅ **Comprehensive Number Entities**: All configurable parameters are exposed as number entities
2. ✅ **Clear Organization**: Dashboard is well-organized into logical sections
3. ✅ **Status Visibility**: Current operation status is clearly displayed
4. ✅ **Aggregate Metrics**: Summary metrics (total energy, revenue, cost) are shown
5. ✅ **Switch Controls**: All enable/disable switches are accessible

### Minor Improvements

1. **Add unit clarifications**:
   - `forced_discharge_hours` should clearly show "0 = unlimited" in the dashboard (already in entity name but could be in description)

2. **Add contextual help**:
   - Consider adding markdown sections explaining what each setting does
   - Example: "Min Sell Price: Only discharge when price exceeds this threshold"

3. **Add status indicators**:
   - Show current battery level alongside battery settings
   - Show current solar power alongside solar threshold

## Summary Statistics

| Category | Total Entities | In Dashboard | Missing/Partial | Completeness |
|----------|---------------|--------------|-----------------|--------------|
| Number Entities | 10 | 10 | 0 | 100% |
| Switch Entities | 4 | 4 | 0 | 100% |
| Binary Sensors | 6 | 6 | 0 | 100% |
| Sensor Main States | 3 | 3 | 0 | 100% |
| Sensor Attributes | ~20 | 12 | 8 | 60% |
| **Overall** | **43** | **35** | **8** | **81%** |

## Conclusion

**Main Entities**: 100% complete - all controllable entities are represented in the dashboard.

**Critical Gap**: Detailed time slot information (individual slot times, prices, energy amounts) is available in sensor attributes but **not displayed in the dashboard**. This represents the most significant usability gap.

**Impact**:
- Users can see **when** operations will occur in aggregate (sensor state text)
- Users **cannot** see individual slot timings, which is critical for:
  - Planning daily activities
  - Understanding why specific slots were chosen
  - Debugging unexpected behavior
  - Building custom automations

**Recommendation**: Implement Priority 1 and Priority 4 recommendations to expose time slot details in a user-friendly timeline format.

## Next Steps

1. Update dashboard YAML with individual slot displays
2. Add arbitrage opportunity details
3. Add switch descriptions via secondary_info
4. Consider creating a dedicated "Timeline View" section
5. Test markdown rendering with actual data
6. Document new dashboard features
