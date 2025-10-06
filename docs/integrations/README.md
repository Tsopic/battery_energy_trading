# Integration Guides

Documentation for integrating Battery Energy Trading with third-party systems and inverters.

## Available Integrations

### Sungrow Inverters

- **[Sungrow Integration Guide](sungrow.md)** - Complete guide for Sungrow SHx inverter integration
  - Automatic entity detection
  - Supported inverter models
  - Automation examples
  - Control strategies

- **[Sungrow Entity Reference](sungrow-reference.md)** - Complete entity documentation
  - Battery entities
  - Solar entities
  - Control entities
  - Monitoring entities

## Supported Hardware

The integration currently has built-in support for:

- **Sungrow SHx Inverters** - Full auto-detection and configuration
  - SH5.0RT/SH5.0RT-20 (5kW)
  - SH6.0RT/SH6.0RT-20 (6kW)
  - SH8.0RT/SH8.0RT-20 (8kW)
  - SH10RT/SH10RT-20 (10kW)
  - SH3.6RS, SH4.6RS, SH5.0RS, SH6.0RS

## Requirements

### Nord Pool Integration (Required)

Battery Energy Trading requires the Nord Pool integration:
- **Repository**: https://github.com/custom-components/nordpool
- **Installation**: Via HACS or manual
- **Configuration**: Must have `raw_today` price data attribute

### Sungrow Integration (Optional)

For automatic Sungrow detection:
- **Repository**: https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/
- **Installation**: Via HACS or manual
- **Benefits**: Auto-detects battery level, capacity, solar power, charge/discharge rates

## Generic Battery Systems

For non-Sungrow systems:

1. Configure Nord Pool integration
2. Install Battery Energy Trading
3. Select manual configuration during setup
4. Provide entity IDs for:
   - Battery level (%)
   - Battery capacity (kWh)
   - Solar power (W) - optional
   - Charge/discharge rates (kW)

The integration will work with any battery system that provides these entities in Home Assistant.

## Future Integrations

Planned support for:
- Growatt inverters
- Fronius inverters
- SolarEdge inverters
- Generic MQTT battery systems

Community contributions welcome!

## Contributing Integration Support

To add support for a new inverter/battery system:

1. Study existing `sungrow_helper.py` implementation
2. Create auto-detection helper for your system
3. Add inverter specifications (charge/discharge rates)
4. Write integration documentation
5. Submit pull request

See [Development Guide](../development/README.md) for contribution workflow.
