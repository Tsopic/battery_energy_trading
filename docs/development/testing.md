# Running Tests

This document explains how to run tests for the Battery Energy Trading integration.

## Quick Test (No Dependencies Required)

The core modules can be tested without installing Home Assistant:

### Test Energy Optimizer

```bash
python3 -c "
import sys
from datetime import datetime, timedelta
sys.path.insert(0, 'custom_components/battery_energy_trading')
from energy_optimizer import EnergyOptimizer

# Create test data
optimizer = EnergyOptimizer()
prices = [
    {'start': datetime(2025, 1, 1, h, 0), 
     'end': datetime(2025, 1, 1, h, 0, 15), 
     'value': 0.10 + h * 0.01}
    for h in range(24)
]

# Test discharge slot selection
slots = optimizer.select_discharge_slots(
    raw_prices=prices,
    min_sell_price=0.15,
    battery_capacity=10.0,
    battery_level=80.0,
    discharge_rate=5.0,
    max_slots=3
)

print(f'✓ Selected {len(slots)} discharge slots')
assert len(slots) > 0, 'Should select some slots'
print('✓ Energy optimizer tests passed!')
"
```

### Test Sungrow Helper

```bash
python3 -c "
import sys
from unittest.mock import MagicMock
sys.path.insert(0, 'custom_components/battery_energy_trading')
from sungrow_helper import SungrowHelper

helper = SungrowHelper(MagicMock())

# Test inverter specs
specs = helper.get_inverter_specs('SH10RT')
assert specs['max_charge_kw'] == 10.0
print(f'✓ SH10RT: {specs}')

# Test battery capacity
capacity = helper.get_battery_capacity('SBR128')
assert capacity == 12.8
print(f'✓ SBR128: {capacity} kWh')

print('✓ Sungrow helper tests passed!')
"
```

## Comprehensive Tests

See `TEST_RESULTS.md` for detailed test results including:
- Discharge slot selection with realistic pricing
- Charging slot selection
- Arbitrage opportunity detection
- Edge case handling
- All supported Sungrow models

## Full Test Suite (Requires Home Assistant)

To run the complete test suite with pytest:

```bash
# Install dependencies
pip install pytest pytest-asyncio pytest-homeassistant-custom-component

# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=custom_components.battery_energy_trading --cov-report=html tests/
```

**Note:** The full pytest suite requires Home Assistant to be installed, which has many dependencies. The quick tests above cover the core functionality without requiring Home Assistant.

## Test Results

See `TEST_RESULTS.md` for the latest test results and coverage metrics.
