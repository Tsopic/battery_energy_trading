# Battery Energy Trading Documentation

Complete documentation index for the Battery Energy Trading Home Assistant integration.

## Quick Start

- **[Installation Guide](../INSTALLATION.md)** - Install via HACS, pip, or manually
- **[Main README](../README.md)** - Project overview, features, and quick start
- **[Changelog](../CHANGELOG.md)** - Version history and release notes

## Documentation Sections

### 📖 User Guide

End-user documentation for installation, configuration, and usage.

**[User Guide Index](user-guide/README.md)**

- [Installation Guide](../INSTALLATION.md) - HACS, pip, and manual installation
- [Automatic Trading Setup](user-guide/automatic-trading-setup.md) - ✨ NEW: Automated setup with generated automations
- [Dashboard Setup](user-guide/dashboard-setup.md) - Dashboard installation and configuration
- [Dashboard Entity Reference](user-guide/dashboard-entity-reference.md) - Entity list and descriptions
- [Terminology Guide](TERMINOLOGY.md) - Understanding slots, hours, and key concepts

### 🔌 Integration Guides

Documentation for third-party integrations and inverter systems.

**[Integrations Index](integrations/README.md)**

- [Sungrow Integration](integrations/sungrow.md) - Sungrow inverter integration guide
- [Sungrow Entity Reference](integrations/sungrow-reference.md) - Complete Sungrow entity documentation

### 🛠️ Development

Documentation for developers and contributors.

**[Development Index](development/README.md)**

- [Testing Guide](development/testing.md) - Running tests, coverage, CI/CD
- [Manual Testing Checklist](development/manual-testing-checklist.md) - Manual test scenarios
- [Features Documentation](development/features.md) - Feature details and implementation
- [Release Process](development/release-process.md) - Version management and releases
- [Development History](development/history/README.md) - Historical implementation logs

### 🔧 API Reference

Technical API documentation (in development).

**[API Documentation Index](api/README.md)**

- Energy Optimizer - Core optimization algorithms (coming soon)
- Sungrow Helper - Auto-detection utilities (coming soon)
- Configuration Flow - Setup wizard (coming soon)
- Entity Platforms - Sensors, binary sensors, numbers, switches (coming soon)

## Additional Resources

### Project Files
- **[CLAUDE.md](../CLAUDE.md)** - AI assistant guidelines and architecture documentation
- **[Documentation Guidelines](DOCUMENTATION_GUIDELINES.md)** - Documentation standards and workflow
- **[LICENSE](../LICENSE)** - MIT License
- **[Contributing](development/README.md#contributing)** - Contribution guidelines

### External Links
- **[GitHub Repository](https://github.com/Tsopic/battery_energy_trading)** - Source code and issues
- **[HACS](https://hacs.xyz/)** - Home Assistant Community Store
- **[Nord Pool Integration](https://github.com/custom-components/nordpool)** - Required dependency
- **[Sungrow Integration](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/)** - Optional for auto-detection

## Documentation Organization

### Directory Structure

```
docs/
├── README.md                          # This file - main documentation index
├── TERMINOLOGY.md                     # Key concepts and terminology
│
├── user-guide/                        # End-user documentation
│   ├── README.md                      # User guide index
│   ├── automatic-trading-setup.md     # Automatic automation generation (NEW)
│   ├── dashboard-setup.md             # Dashboard setup guide
│   └── dashboard-entity-reference.md  # Dashboard entity list
│
├── integrations/                      # Third-party integration guides
│   ├── README.md                      # Integrations index
│   ├── sungrow.md                     # Sungrow integration guide
│   └── sungrow-reference.md           # Sungrow entity reference
│
├── development/                       # Developer documentation
│   ├── README.md                      # Development index
│   ├── testing.md                     # Testing guide
│   ├── manual-testing-checklist.md    # Manual test scenarios
│   ├── features.md                    # Feature documentation
│   ├── release-process.md             # Release workflow
│   │
│   └── history/                       # Historical documentation
│       ├── README.md                  # History index
│       └── *.md                       # Implementation logs (2025-10)
│
└── api/                               # API documentation (in development)
    └── README.md                      # API index
```

### Navigation Tips

1. **Start with the User Guide** if you're installing and using the integration
2. **Check Integrations** for Sungrow or other inverter-specific documentation
3. **Visit Development** if you're contributing code or running tests
4. **Browse History** to understand past architectural decisions

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/Tsopic/battery_energy_trading/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Tsopic/battery_energy_trading/discussions)
- **Documentation Bugs**: Report via GitHub Issues with `documentation` label

## Documentation Guidelines

See [Development Guide](development/README.md#contributing) for:
- File naming conventions
- When to archive vs keep in main docs
- Cross-reference standards
- Index file requirements
