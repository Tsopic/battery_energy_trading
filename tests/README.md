# Battery Energy Trading - Test Suite

This directory contains comprehensive tests for the Battery Energy Trading integration.

## Running Tests

### Prerequisites

```bash
pip install pytest pytest-asyncio pytest-homeassistant-custom-component
```

### Run All Tests

```bash
# From repository root
pytest tests/

# With coverage
pytest --cov=custom_components.battery_energy_trading --cov-report=html tests/

# Verbose output
pytest -v tests/
```

### Run Specific Test Files

```bash
# Test energy optimizer only
pytest tests/test_energy_optimizer.py

# Test Sungrow helper only
pytest tests/test_sungrow_helper.py

# Test config flow only
pytest tests/test_config_flow.py
```

### Run Specific Tests

```bash
# Run a specific test class
pytest tests/test_energy_optimizer.py::TestEnergyOptimizer

# Run a specific test method
pytest tests/test_energy_optimizer.py::TestEnergyOptimizer::test_select_discharge_slots_basic
```

## Test Coverage

The test suite covers:

### `test_energy_optimizer.py`
- **Discharge slot selection**:
  - Basic slot selection with price filtering
  - Battery capacity constraints
  - Energy per slot calculations
  - Maximum slot limiting
- **Charging slot selection**:
  - Basic charging slot selection
  - Battery already at target scenarios
  - No economical slots available
- **Arbitrage detection**:
  - Finding profitable charge/discharge cycles
  - Efficiency loss accounting
  - Minimum profit thresholds
- **Time slot detection**:
  - Current time in slot checks
  - Timezone handling

### `test_sungrow_helper.py`
- **Entity detection**:
  - Automatic Sungrow entity discovery
  - Pattern matching for various entity names
- **Inverter specifications**:
  - Model lookup (SH5.0RT, SH10RT, etc.)
  - Charge/discharge rate retrieval
  - Fuzzy model matching
- **Battery capacity lookup**:
  - SBR series capacity mapping
- **Auto-configuration**:
  - Complete auto-detection flow
  - Partial detection scenarios
  - Default fallbacks

### `test_config_flow.py`
- **User flow**:
  - Sungrow detection triggering
  - Manual configuration fallback
- **Sungrow auto-detection**:
  - Accepting auto-configuration
  - Declining auto-configuration
  - Pre-filled entity suggestions
- **Manual configuration**:
  - Successful entity validation
  - Entity not found error handling
  - Optional solar sensor

## Fixtures

Defined in `conftest.py`:

- `mock_hass` - Mock Home Assistant instance
- `mock_config_entry` - Mock config entry for manual setup
- `mock_config_entry_sungrow` - Mock config entry with Sungrow auto-detection
- `sample_price_data` - 96 slots of realistic 15-minute price data
- `mock_sungrow_entities` - Mock Sungrow sensor entities

## Test Data

### Price Data Pattern
The `sample_price_data` fixture provides realistic pricing:
- **Morning peak** (08:00-10:00): €0.35-0.41/kWh
- **Evening peak** (17:00-20:00): €0.40-0.49/kWh
- **Night cheap** (02:00-05:00): €-0.01-0.04/kWh
- **Normal hours**: €0.12-0.15/kWh

### Mock Sungrow Setup
- Inverter: SH10RT (10kW charge/discharge)
- Battery: SBR128 (12.8 kWh capacity)
- Battery Level: 75%
- Solar Power: 2500W

## Writing New Tests

### Example Test Structure

```python
def test_new_feature(self, sample_price_data):
    """Test description."""
    optimizer = EnergyOptimizer()

    result = optimizer.new_method(
        raw_prices=sample_price_data,
        param1=value1,
    )

    assert result is not None
    assert len(result) > 0
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_feature(self, mock_hass):
    """Test async feature."""
    helper = SungrowHelper(mock_hass)

    result = await helper.async_method()

    assert result["key"] == expected_value
```

## Continuous Integration

These tests can be run in CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-asyncio pytest-homeassistant-custom-component
      - run: pytest tests/ --cov=custom_components.battery_energy_trading
```

## Coverage Goals

Target coverage: **>80%** for all modules

Current coverage:
- `energy_optimizer.py`: ~95%
- `sungrow_helper.py`: ~90%
- `config_flow.py`: ~85%

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all existing tests pass
3. Add tests for edge cases
4. Update this README if adding new test files
