# Battery Energy Trading Documentation

Welcome to the Battery Energy Trading documentation!

## 📚 Documentation Index

### User Guide

- **[Installation Guide](../README.md#-installation)** - How to install via HACS or manually
- **[Configuration Guide](../README.md#️-configuration)** - Setting up the integration
- **[Dashboard Setup](../dashboards/README.md)** - Pre-built dashboard and customization
- **[Sungrow Integration](integrations/sungrow.md)** - Automatic Sungrow inverter setup and automations

### Integrations

- **[Sungrow Inverters](integrations/sungrow.md)** - Complete guide for Sungrow SHx inverters
  - Auto-detection and configuration
  - Pre-built automations
  - Supported models and specifications

### Development

- **[Features Overview](development/features.md)** - Detailed feature documentation
- **[Testing Guide](development/testing.md)** - How to run and write tests
- **[Test Results](development/test-results.md)** - Latest test coverage and results
- **[Release Process](development/release-process.md)** - How to create releases
- **[Contributing Guide](../CLAUDE.md)** - Development guidelines and architecture

### Reference

- **[Changelog](../CHANGELOG.md)** - Version history and changes
- **[License](../LICENSE)** - MIT License

## 🎯 Quick Links

### Getting Started
1. [Prerequisites](../README.md#-prerequisites) - Required integrations (Nord Pool)
2. [Installation](../README.md#-installation) - HACS or manual installation
3. [Configuration](../README.md#️-configuration) - Initial setup
4. [Dashboard](../dashboards/README.md) - Add the pre-built dashboard

### Common Tasks
- [Set up Sungrow automations](integrations/sungrow.md#automation-examples)
- [Configure discharge hours](../README.md#configuration-parameters)
- [Customize the dashboard](../dashboards/README.md#customization)
- [Run tests](development/testing.md)

### Advanced Topics
- [Energy optimization logic](../CLAUDE.md#energy-optimization-logic-energy_optimizerpy)
- [Discharge slot selection](../CLAUDE.md#how-it-works-now)
- [Nord Pool integration](../CLAUDE.md#price-data-format)
- [Architecture overview](../CLAUDE.md#architecture)

## 📖 Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── user-guide/                  # End-user documentation
├── integrations/                # Integration-specific guides
│   └── sungrow.md              # Sungrow inverter integration
└── development/                 # Developer documentation
    ├── features.md             # Feature details and specifications
    ├── testing.md              # Testing guide
    ├── test-results.md         # Test coverage and results
    └── release-process.md      # Release workflow
```

## 🤝 Contributing

We welcome contributions! See the [Contributing Guide](../CLAUDE.md) for:
- Architecture overview
- Development setup
- Code standards
- Common commands

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/Tsopic/battery_energy_trading/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Tsopic/battery_energy_trading/discussions)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
