# Test Improvement Plan - Integration & Sungrow Coverage

**Date**: 2025-10-02
**Current Coverage**: 89.74%
**Target Coverage**: 95%+

---

## Executive Summary

This plan outlines improvements to integration testing, focusing on:
1. **Real Home Assistant integration testing** - Move from mocks to actual HA core
2. **Comprehensive Sungrow entity coverage** - Test all battery data available from Sungrow Modbus integration
3. **Integration test patterns** - Follow HA best practices for robust testing

---

## Current Test Coverage Analysis

### Coverage by Module (from `docs/development/testing.md`)

```
Module                  Statements    Missing    Coverage
---------------------------------------------------------
__init__.py                   50          0      100.00%
base_entity.py                60          0      100.00%
const.py                      57          0      100.00%
number.py                     40          0      100.00%
switch.py                     41          0      100.00%
binary_sensor.py             190          4       95.22%
sensor.py                    193         12       89.71%
sungrow_helper.py             84          3       92.59%
energy_optimizer.py          378         49       84.38%  ← Main gap
config_flow.py                89         13       78.74%  ← Main gap
---------------------------------------------------------
TOTAL                       1182         81       89.74%
```

### Current Test Files

1. ✅ `test_base_entity.py` - 100% coverage (34 tests)
2. ✅ `test_binary_sensors.py` - 95.22% coverage (45 tests)
3. ✅ `test_sensors.py` - 89.71% coverage
4. ✅ `test_numbers.py` - 100% coverage
5. ✅ `test_switches.py` - 100% coverage
6. ✅ `test_sungrow_helper.py` - 92.59% coverage (19 tests)
7. ⚠️ `test_energy_optimizer.py` - 84.38% coverage (needs expansion)
8. ⚠️ `test_config_flow.py` - 78.74% coverage (has failing tests)
9. ✅ `test_slot_combination.py` - Multi-peak discharge tests
10. ✅ `test_init.py` - Integration lifecycle tests

---

## Gap Analysis

### 1. Missing Integration Test Patterns

**Current Approach**: Heavy mocking with `MagicMock`
- Mock `hass`, `config_entry`, entities
- Unit testing approach, not integration testing

**What's Missing**:
- ❌ Real Home Assistant core testing
- ❌ Actual entity state management through `hass.states`
- ❌ Real config entry lifecycle (`async_setup_entry`, `async_unload_entry`)
- ❌ Device and entity registry interactions
- ❌ Coordinator update testing with real state changes

**Best Practice** (from HA docs):
> "Interact with integration through core systems:
> - Use `hass.states` to check entity states
> - Use `hass.services` to perform service actions"

### 2. Sungrow Battery Data Coverage

**Available from Sungrow Modbus Integration** (from research):

| Entity | Entity ID | Modbus Address | Current Test Coverage |
|--------|-----------|----------------|----------------------|
| Battery Level (SOC) | `sensor.battery_level` | 13022 | ✅ Tested |
| Battery Capacity | `sensor.battery_capacity` | 5638 | ✅ Tested |
| Battery Voltage | `sensor.battery_voltage` | 13019 | ❌ Not tested |
| Battery Current | `sensor.battery_current` | 13020 | ❌ Not tested |
| Battery Power | `sensor.battery_power_raw` | 13021 | ❌ Not tested |
| Battery Temperature | `sensor.battery_temperature` | 13024 | ❌ Not tested |
| Battery State of Health | `sensor.battery_state_of_health` | 13023 | ❌ Not tested |
| Total DC Power (Solar) | `sensor.total_dc_power` | 5016 | ✅ Tested |
| Device Type | `sensor.sungrow_device_type` | Template | ✅ Tested |

**Derived/Calculated Entities** (not tested):
- ❌ `sensor.battery_level_nominal` - Calculated between min/max SoC
- ❌ `sensor.battery_charge` - Current charge in kWh
- ❌ `sensor.battery_charge_nominal` - Nominal capacity
- ❌ `sensor.battery_charge_health_rated` - Health-adjusted capacity
- ❌ Signed battery power calculations
- ❌ Battery charging/discharging power separation

### 3. Config Flow Testing Gaps

**Current Issues**:
- 5 tests failing in `test_config_flow.py`
- Missing validation tests
- No dashboard wizard flow testing
- Missing error handling scenarios

**Needed Tests**:
- ✅ Nord Pool validation (partially covered)
- ❌ Entity validation (must exist in state machine)
- ❌ `raw_today` attribute validation
- ❌ Dashboard setup step testing
- ❌ Options flow (reconfigure)
- ❌ Migration testing (if schema changes)

### 4. Energy Optimizer Coverage Gaps

**Current Coverage**: 84.38% (49 missing statements)

**What's Missing**:
- ❌ Edge cases in multi-day optimization
- ❌ Battery efficiency calculations
- ❌ Slot combination optimization paths
- ❌ Error handling in price data processing
- ❌ Timezone handling
- ❌ Tomorrow's prices integration

---

## Improvement Plan

### Phase 1: Fix Config Flow Tests (High Priority)

**Goal**: Fix 5 failing tests, achieve 90%+ coverage

**Tasks**:
1. Update `test_config_flow.py` to use proper HA test fixtures
2. Replace `MagicMock` with `HomeAssistant` fixture
3. Use `MockConfigEntry` from `tests/common.py`
4. Test actual config entry lifecycle
5. Add validation error tests

**Files to modify**:
- `tests/test_config_flow.py`

**Estimated effort**: 2-3 hours

### Phase 2: Add Integration Test Fixtures (High Priority)

**Goal**: Create proper HA integration test fixtures

**Tasks**:
1. Add `hass` fixture from `pytest-homeassistant-custom-component`
2. Add `enable_custom_integrations` fixture
3. Create fixtures for realistic entity states
4. Create Nord Pool mock with actual state machine integration
5. Create Sungrow entity fixtures with full battery data

**Files to create/modify**:
- `tests/conftest.py` - Add HA fixtures
- `tests/fixtures/sungrow_battery_data.json` - Sample battery states
- `tests/fixtures/nordpool_prices.json` - Sample price data

**Example fixture**:
```python
@pytest.fixture
def sungrow_battery_entities(hass):
    """Create Sungrow battery entities in state machine."""
    # Battery Level (SOC)
    hass.states.async_set(
        "sensor.battery_level",
        "75",
        {
            "unit_of_measurement": "%",
            "device_class": "battery",
            "friendly_name": "Battery Level",
        }
    )

    # Battery Voltage
    hass.states.async_set(
        "sensor.battery_voltage",
        "52.4",
        {
            "unit_of_measurement": "V",
            "friendly_name": "Battery Voltage",
        }
    )

    # Battery Current
    hass.states.async_set(
        "sensor.battery_current",
        "12.5",
        {
            "unit_of_measurement": "A",
            "friendly_name": "Battery Current",
        }
    )

    # Battery Power
    hass.states.async_set(
        "sensor.battery_power_raw",
        "655",  # 52.4V * 12.5A ≈ 655W
        {
            "unit_of_measurement": "W",
            "friendly_name": "Battery Power",
        }
    )

    # Battery Temperature
    hass.states.async_set(
        "sensor.battery_temperature",
        "18.5",
        {
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "friendly_name": "Battery Temperature",
        }
    )

    # Battery State of Health
    hass.states.async_set(
        "sensor.battery_state_of_health",
        "98",
        {
            "unit_of_measurement": "%",
            "friendly_name": "Battery State of Health",
        }
    )

    # Battery Capacity
    hass.states.async_set(
        "sensor.battery_capacity",
        "12.8",
        {
            "unit_of_measurement": "kWh",
            "friendly_name": "Battery Capacity",
        }
    )

    return hass
```

**Estimated effort**: 3-4 hours

### Phase 3: Expand Sungrow Helper Tests (Medium Priority)

**Goal**: Test all Sungrow battery data detection and processing

**Tasks**:
1. Add tests for voltage, current, power detection
2. Add tests for temperature detection
3. Add tests for state of health detection
4. Add tests for derived/calculated entities
5. Add tests for multiple battery configurations
6. Add tests for different Sungrow inverter models

**New test cases**:
```python
def test_detect_battery_voltage_entity(hass, sungrow_battery_entities):
    """Test battery voltage detection."""
    helper = SungrowHelper(hass)
    detected = helper.detect_sungrow_entities()
    assert detected["battery_voltage"] == "sensor.battery_voltage"

def test_detect_battery_temperature_entity(hass, sungrow_battery_entities):
    """Test battery temperature detection."""
    helper = SungrowHelper(hass)
    detected = helper.detect_sungrow_entities()
    assert detected["battery_temperature"] == "sensor.battery_temperature"

def test_detect_battery_health_entity(hass, sungrow_battery_entities):
    """Test battery state of health detection."""
    helper = SungrowHelper(hass)
    detected = helper.detect_sungrow_entities()
    assert detected["battery_health"] == "sensor.battery_state_of_health"

def test_calculate_battery_power_from_voltage_current(hass):
    """Test derived battery power calculation."""
    # Power = Voltage × Current
    # If integration provides voltage and current, validate power calculation
    pass
```

**Files to modify**:
- `custom_components/battery_energy_trading/sungrow_helper.py` - Add new entity patterns
- `tests/test_sungrow_helper.py` - Add new tests

**Estimated effort**: 2-3 hours

### Phase 4: Integration Lifecycle Tests (Medium Priority)

**Goal**: Test full integration setup/teardown with real HA core

**Tasks**:
1. Test `async_setup_entry` with real config entry
2. Test entity registration in device/entity registry
3. Test coordinator updates
4. Test entity state changes through coordinator
5. Test `async_unload_entry` cleanup
6. Test entity availability

**Example test**:
```python
async def test_integration_setup_creates_entities(hass, config_entry):
    """Test integration setup creates all expected entities."""
    # Setup integration
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    # Verify entities created
    entity_registry = er.async_get(hass)

    # Check binary sensors
    assert entity_registry.async_get("binary_sensor.battery_energy_trading_forced_discharge")
    assert entity_registry.async_get("binary_sensor.battery_energy_trading_cheapest_hours")

    # Check sensors
    assert entity_registry.async_get("sensor.battery_energy_trading_discharge_time_slots")

    # Check configuration sensors
    assert entity_registry.async_get("sensor.battery_energy_trading_configuration")

async def test_coordinator_updates_entity_states(hass, config_entry):
    """Test coordinator updates propagate to entity states."""
    # Setup integration
    await async_setup_component(hass, DOMAIN, {})

    # Wait for coordinator update
    await hass.async_block_till_done()

    # Verify entity states updated
    state = hass.states.get("sensor.battery_energy_trading_discharge_time_slots")
    assert state is not None
    assert state.state != "unknown"
```

**Files to create**:
- `tests/test_integration_lifecycle.py` - New file

**Estimated effort**: 4-5 hours

### Phase 5: Energy Optimizer Edge Cases (Low Priority)

**Goal**: Increase energy_optimizer.py coverage from 84% to 95%+

**Tasks**:
1. Add tests for multi-day optimization edge cases
2. Add tests for battery efficiency calculations
3. Add tests for timezone handling
4. Add tests for tomorrow's prices
5. Add tests for slot combination optimization
6. Add tests for error handling

**Files to modify**:
- `tests/test_energy_optimizer.py`

**Estimated effort**: 3-4 hours

### Phase 6: Binary Sensor Real Integration Tests (Low Priority)

**Goal**: Test binary sensors through HA state machine

**Tasks**:
1. Replace mocks with real `hass.states` interactions
2. Test coordinator-driven state updates
3. Test entity availability changes
4. Test tracked entity changes

**Example test**:
```python
async def test_forced_discharge_sensor_state_changes(hass):
    """Test forced discharge sensor responds to coordinator updates."""
    # Setup Nord Pool with high prices
    hass.states.async_set("sensor.nordpool", "0.45", {
        "raw_today": [...high_price_data...]
    })

    # Setup battery entities
    hass.states.async_set("sensor.battery_level", "80")
    hass.states.async_set("sensor.battery_capacity", "12.8")

    # Setup integration
    await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    # Check binary sensor state
    state = hass.states.get("binary_sensor.battery_energy_trading_forced_discharge")
    assert state.state == "on"  # Should be on during high price period

    # Update Nord Pool with low prices
    hass.states.async_set("sensor.nordpool", "0.05", {
        "raw_today": [...low_price_data...]
    })

    # Trigger coordinator update
    await hass.async_block_till_done()

    # Verify sensor updated
    state = hass.states.get("binary_sensor.battery_energy_trading_forced_discharge")
    assert state.state == "off"  # Should turn off with low prices
```

**Files to modify**:
- `tests/test_binary_sensors.py`

**Estimated effort**: 2-3 hours

---

## Implementation Priority

### High Priority (Week 1)
1. ✅ Fix config flow tests
2. ✅ Add proper HA integration fixtures
3. ✅ Update conftest.py with real fixtures

### Medium Priority (Week 2)
4. ✅ Expand Sungrow helper tests
5. ✅ Add integration lifecycle tests
6. ✅ Test coordinator behavior

### Low Priority (Week 3+)
7. ⏳ Energy optimizer edge cases
8. ⏳ Binary sensor integration tests
9. ⏳ Add snapshot testing for complex states

---

## Expected Coverage Improvements

| Module | Current | Target | Effort |
|--------|---------|--------|--------|
| config_flow.py | 78.74% | 95%+ | High |
| energy_optimizer.py | 84.38% | 95%+ | Medium |
| sungrow_helper.py | 92.59% | 98%+ | Low |
| binary_sensor.py | 95.22% | 98%+ | Low |
| sensor.py | 89.71% | 95%+ | Medium |
| **TOTAL** | **89.74%** | **95%+** | **16-22 hours** |

---

## Testing Best Practices to Follow

### From Home Assistant Developer Docs

1. **Use Core Interfaces**:
   ```python
   # Good ✅
   state = hass.states.get("sensor.battery_level")

   # Bad ❌
   state = integration.battery_sensor.state
   ```

2. **Mock External Dependencies Only**:
   ```python
   # Mock Nord Pool integration (external)
   @patch("custom_components.nordpool.sensor.NordPoolSensor")

   # Don't mock HA core
   hass = await async_test_home_assistant()  # Real HA instance
   ```

3. **Test Through Services**:
   ```python
   # Test service calls
   await hass.services.async_call(
       "battery_energy_trading",
       "sync_sungrow_parameters",
       blocking=True
   )
   ```

4. **Use Snapshot Testing for Complex States**:
   ```python
   def test_discharge_slots_attributes(hass, snapshot):
       state = hass.states.get("sensor.battery_energy_trading_discharge_time_slots")
       assert state.attributes == snapshot
   ```

5. **Enable Custom Integrations**:
   ```python
   @pytest.fixture(autouse=True)
   def enable_custom_integrations(hass):
       """Enable loading custom integrations."""
       hass.data["custom_components"] = {}
   ```

---

## New Test Files to Create

1. `tests/test_integration_lifecycle.py` - Integration setup/teardown
2. `tests/fixtures/sungrow_battery_data.json` - Sample Sungrow data
3. `tests/fixtures/nordpool_prices.json` - Sample Nord Pool prices
4. `tests/test_real_integration.py` - End-to-end integration tests
5. `tests/snapshots/` - Snapshot test data

---

## Success Metrics

### Coverage Targets
- ✅ Overall: 95%+ (from 89.74%)
- ✅ config_flow.py: 95%+ (from 78.74%)
- ✅ energy_optimizer.py: 95%+ (from 84.38%)
- ✅ All other modules: 95%+

### Test Quality Metrics
- ✅ All tests passing
- ✅ Zero flaky tests
- ✅ Tests use real HA fixtures (not excessive mocking)
- ✅ Integration tests cover full lifecycle
- ✅ All Sungrow battery entities tested

### Documentation
- ✅ Update `docs/development/testing.md` with new patterns
- ✅ Document Sungrow entity coverage
- ✅ Add integration testing examples

---

## Risks & Mitigation

### Risk 1: Breaking Existing Tests
**Mitigation**: Incremental changes, run tests after each modification

### Risk 2: HA Fixture Compatibility
**Mitigation**: Pin pytest-homeassistant-custom-component version, test with multiple HA versions

### Risk 3: Test Runtime
**Mitigation**: Use pytest-xdist for parallel execution, optimize slow tests

---

## Next Steps

1. ✅ Review and approve this plan
2. ⏳ Create feature branch: `feature/improve-integration-tests`
3. ⏳ Implement Phase 1 (config flow fixes)
4. ⏳ Implement Phase 2 (HA fixtures)
5. ⏳ Continue through phases 3-6
6. ⏳ Update documentation
7. ⏳ Create PR with improvements

---

## References

- [Home Assistant Testing Docs](https://developers.home-assistant.io/docs/development_testing/)
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
- [Sungrow Modbus Integration](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant)
- [Current Testing Guide](docs/development/testing.md)
