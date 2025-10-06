# Installation Guide

## Methods

### 1. HACS (Recommended)

The Battery Energy Trading integration is designed to be installed via HACS (Home Assistant Community Store).

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add this repository: `https://github.com/Tsopic/battery_energy_trading`
5. Category: Integration
6. Click "ADD"
7. Find "Battery Energy Trading" in HACS
8. Click "DOWNLOAD"
9. Restart Home Assistant

### 2. Manual Installation

#### Option A: Copy Files

```bash
# Navigate to your Home Assistant config directory
cd /path/to/homeassistant/config

# Create custom_components directory if it doesn't exist
mkdir -p custom_components

# Clone the repository
git clone https://github.com/Tsopic/battery_energy_trading.git /tmp/battery_energy_trading

# Copy the custom component
cp -r /tmp/battery_energy_trading/custom_components/battery_energy_trading \
      custom_components/

# Restart Home Assistant
```

#### Option B: Using pip (Development Install)

For development or testing:

```bash
# Clone the repository
git clone https://github.com/Tsopic/battery_energy_trading.git
cd battery_energy_trading

# Install in development mode
pip install -e .

# Or install with test dependencies
pip install -e ".[dev]"
```

### 3. Package Manager Installation

The component can be installed as a Python package:

```bash
# Install from source
pip install git+https://github.com/Tsopic/battery_energy_trading.git

# Or build and install locally
git clone https://github.com/Tsopic/battery_energy_trading.git
cd battery_energy_trading
pip install .
```

Then copy the component to your Home Assistant `custom_components` directory:

```bash
# Find where the package was installed
python -c "import custom_components.battery_energy_trading; print(custom_components.battery_energy_trading.__file__)"

# Copy to Home Assistant
cp -r $(python -c "import os,custom_components.battery_energy_trading as m; print(os.path.dirname(m.__file__))") \
      /path/to/homeassistant/config/custom_components/battery_energy_trading
```

## Prerequisites

- **Home Assistant**: 2023.1.0 or newer (2024.1.0+ recommended)
- **Python**: 3.11 or newer
- **Nord Pool Integration**: Must be installed and configured
- **Optional**: Sungrow integration for automatic inverter detection

## Dependencies

The integration has **no external runtime dependencies** - it uses only Home Assistant built-in libraries.

### Development Dependencies

For development and testing:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Or install test dependencies only
pip install -e ".[test]"
```

This installs:
- pytest >= 8.0.0
- pytest-asyncio >= 0.23.0
- pytest-cov >= 4.1.0
- pytest-mock >= 3.12.0
- pytest-homeassistant-custom-component >= 0.13.0
- homeassistant >= 2024.1.0 (for testing)

## Configuration

After installation:

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Battery Energy Trading"
3. Follow the configuration wizard

### Automatic Configuration (Sungrow)

If you have the Sungrow integration installed, the setup will auto-detect:
- Battery level entity
- Battery capacity entity
- Solar power entity
- Inverter model and charge/discharge rates

### Manual Configuration

If auto-detection is not available, you'll be prompted to manually select:
- Nord Pool price entity
- Battery level entity
- Battery capacity entity
- Optional: Solar power entity
- Optional: Solar forecast entity

## Verification

After installation, verify the integration is working:

1. Check that entities are created:
   - `sensor.battery_energy_trading_configuration`
   - `sensor.battery_energy_trading_discharge_time_slots`
   - `sensor.battery_energy_trading_charging_time_slots`
   - `binary_sensor.battery_energy_trading_forced_discharge`
   - And others...

2. Check the logs for any errors:
   - Go to **Settings** → **System** → **Logs**
   - Filter by: `battery_energy_trading`

## Updating

### HACS Update
1. Go to HACS → Integrations
2. Find "Battery Energy Trading"
3. Click "UPDATE" if available
4. Restart Home Assistant

### Manual Update
```bash
cd /path/to/homeassistant/config/custom_components/battery_energy_trading
git pull
# Restart Home Assistant
```

### Package Manager Update
```bash
pip install --upgrade battery-energy-trading

# Or from source
pip install --upgrade git+https://github.com/Tsopic/battery_energy_trading.git
```

## Troubleshooting

### Integration Not Found
- Verify files are in `custom_components/battery_energy_trading/`
- Check that `manifest.json` exists
- Restart Home Assistant

### Nord Pool Entity Required
- This integration requires the Nord Pool integration
- Install from: https://github.com/custom-components/nordpool
- Configure Nord Pool before setting up Battery Energy Trading

### Entities Not Created
- Check Home Assistant logs for errors
- Verify Nord Pool entity has `raw_today` attribute
- Ensure all required entities exist and are updating

## Support

- **Issues**: https://github.com/Tsopic/battery_energy_trading/issues
- **Documentation**: https://github.com/Tsopic/battery_energy_trading
- **Discussions**: https://github.com/Tsopic/battery_energy_trading/discussions

## Development

To contribute or modify the integration:

```bash
# Clone repository
git clone https://github.com/Tsopic/battery_energy_trading.git
cd battery_energy_trading

# Create virtual environment (Python 3.13+ recommended)
python3.13 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=custom_components.battery_energy_trading --cov-report=html

# View coverage report
open htmlcov/index.html  # On macOS
```

## License

MIT License - see LICENSE file for details.
