# Testing Guide

Complete guide for running tests in the Battery Energy Trading integration.

## Quick Start

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components.battery_energy_trading --cov-report=html
```

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Running Tests](#running-tests)
4. [Test Structure](#test-structure)
5. [Coverage Reports](#coverage-reports)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Python Version

- **Python 3.11+**: Recommended (supports latest Home Assistant)
- **Python 3.13+**: Required for Home Assistant 2025.10.0+

### Required Packages

Test dependencies are defined in `pyproject.toml` under `[project.optional-dependencies.test]`:

```toml
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "pytest-homeassistant-custom-component>=0.13.0",
    "homeassistant>=2024.1.0",
]
```

---

## Installation

### Method 1: Install with Test Dependencies (Recommended)

```bash
# Install package with test dependencies
pip install -e ".[test]"
```

This installs:
- All runtime dependencies
- pytest and plugins
- pytest-homeassistant-custom-component
- Home Assistant (for integration testing)

### Method 2: Manual Installation

```bash
# Install from requirements file
pip install -r requirements_test.txt
```

### Verify Installation

```bash
# Check pytest is installed
pytest --version

# Check homeassistant is installed
python -c "import homeassistant; print(homeassistant.__version__)"
```

---

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_energy_optimizer.py

# Run specific test class
pytest tests/test_energy_optimizer.py::TestEnergyOptimizer

# Run specific test
pytest tests/test_energy_optimizer.py::TestEnergyOptimizer::test_select_discharge_slots_basic
```

### With Coverage

```bash
# Run with coverage report
pytest --cov=custom_components.battery_energy_trading --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=custom_components.battery_energy_trading --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Quick Verification (Core Modules Only)

Test core modules without full Home Assistant installation:

```bash
# Test energy optimizer
pytest tests/test_energy_optimizer.py -v

# Test sungrow helper
pytest tests/test_sungrow_helper.py -v
```

### Failed Tests Only

```bash
# Run only tests that failed last time
pytest --lf

# Run failed tests first, then others
pytest --ff
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
pytest -n auto  # Requires pytest-xdist
```

---

## Test Structure

### Test Files

```
tests/
├── conftest.py                     # Shared fixtures
├── test_energy_optimizer.py        # Energy optimization logic
├── test_sungrow_helper.py          # Sungrow integration
├── test_base_entity.py             # Base entity helpers
├── test_binary_sensors.py          # Binary sensor entities
├── test_sensors.py                 # Sensor entities
├── test_numbers.py                 # Number entities
├── test_switches.py                # Switch entities
├── test_init.py                    # Integration lifecycle
├── test_config_flow.py             # Configuration flow
└── test_slot_combination.py        # Multi-peak discharge logic
```

### Test Categories

#### Unit Tests
- `test_energy_optimizer.py` - Core optimization algorithms
- `test_sungrow_helper.py` - Sungrow auto-detection logic
- `test_base_entity.py` - Helper methods

#### Integration Tests
- `test_binary_sensors.py` - Binary sensor platform
- `test_sensors.py` - Sensor platform
- `test_numbers.py` - Number platform
- `test_switches.py` - Switch platform
- `test_init.py` - Integration setup/teardown
- `test_config_flow.py` - Configuration wizard

#### Feature Tests
- `test_slot_combination.py` - Multi-peak discharge combinations

---

## Coverage Reports

### Current Coverage Stats

Target: **90%**
Current: **89.74%**

### Module Coverage Breakdown

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
energy_optimizer.py          378         49       84.38%
config_flow.py                89         13       78.74%
---------------------------------------------------------
TOTAL                       1182         81       89.74%
```

### Viewing Coverage

```bash
# Terminal report
pytest --cov=custom_components.battery_energy_trading --cov-report=term-missing

# HTML report (interactive)
pytest --cov=custom_components.battery_energy_trading --cov-report=html
open htmlcov/index.html

# JSON report (for tools)
pytest --cov=custom_components.battery_energy_trading --cov-report=json
cat coverage.json
```

### Coverage Configuration

Coverage settings are in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["custom_components/battery_energy_trading"]
branch = true

[tool.coverage.report]
fail_under = 90  # Fail if coverage < 90%
show_missing = true
```

---

## CI/CD Integration

### GitHub Actions

The project uses GitHub Actions for automated testing. See `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run tests with coverage
        run: |
          pytest --cov=custom_components.battery_energy_trading \
                 --cov-report=xml \
                 --cov-report=term-missing

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
```

### Local CI Simulation

```bash
# Run tests exactly as CI does
python -m pytest --cov=custom_components.battery_energy_trading --cov-report=xml --cov-report=term-missing
```

---

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'homeassistant'

**Solution**: Install Home Assistant

```bash
pip install homeassistant>=2024.1.0
```

### Issue: Python version too old

**Error**: `homeassistant requires Python >=3.13.2`

**Solution**: Upgrade Python or use older HA version

```bash
# Option 1: Upgrade Python
python3.13 -m venv .venv
source .venv/bin/activate

# Option 2: Use compatible HA version (not recommended)
pip install homeassistant==2023.7.3  # Python 3.10 compatible
```

### Issue: Tests timing out

**Solution**: Increase timeout

```bash
pytest --timeout=300  # 5 minute timeout
```

### Issue: Network timeouts during installation

**Solution**: Increase pip timeout

```bash
pip install --timeout=300 -r requirements_test.txt
```

### Issue: Import errors in tests

**Solution**: Install package in editable mode

```bash
pip install -e .
```

### Issue: Coverage not showing source

**Solution**: Ensure source is installed in the environment

```bash
pip uninstall battery-energy-trading
pip install -e .
```

---

## Best Practices

### Writing Tests

1. **Use fixtures** - Define reusable test data in `conftest.py`
2. **Test one thing** - Each test should verify one specific behavior
3. **Use descriptive names** - `test_discharge_slots_respects_battery_capacity` not `test_slots`
4. **Mock external dependencies** - Use `MagicMock` for Home Assistant components
5. **Test edge cases** - Empty data, None values, invalid input

### Running Tests During Development

```bash
# Watch mode (re-run on file changes)
pytest-watch

# Or use pytest-testmon (only re-run affected tests)
pytest --testmon
```

### Before Committing

```bash
# Run all tests with coverage
pytest --cov=custom_components.battery_energy_trading --cov-fail-under=90

# Check code formatting (if using black/ruff)
black custom_components tests
ruff check custom_components tests
```

---

## Quick Reference

### Common Commands

```bash
# Install with test deps
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components.battery_energy_trading --cov-report=html

# Run specific test
pytest tests/test_energy_optimizer.py::test_select_discharge_slots_basic -v

# Run failed tests only
pytest --lf

# Run in parallel
pytest -n auto

# Watch mode
pytest-watch
```

### Useful Flags

- `-v` / `--verbose` - Detailed output
- `-s` / `--capture=no` - Show print statements
- `-x` / `--exitfirst` - Stop on first failure
- `--lf` / `--last-failed` - Re-run failed tests
- `--ff` / `--failed-first` - Run failed first
- `-k EXPRESSION` - Run tests matching expression
- `--tb=short` - Shorter tracebacks
- `-n NUM` - Run in parallel (requires pytest-xdist)

---

## See Also

- [Manual Testing Checklist](manual-testing-checklist.md) - Manual test scenarios
- [Test Results Archive](history/test-results-2025-10.md) - Historical test results
- [Testing Implementation](history/testing-implementation-2025-10.md) - How tests were implemented
