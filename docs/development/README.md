# Development Documentation

Documentation for developers contributing to or extending the Battery Energy Trading integration.

## Getting Started

- **[Installation Guide](../../INSTALLATION.md#development)** - Setting up development environment
- **[Testing Guide](testing.md)** - Running tests, coverage reports, and CI/CD integration
- **[Manual Testing Checklist](manual-testing-checklist.md)** - Manual test scenarios and validation

## Features & Architecture

- **[Features Documentation](features.md)** - Detailed feature descriptions and implementation notes
- **[Release Process](release-process.md)** - Version management and release workflow

## Historical Documentation

See [history/](history/) for implementation logs, refactoring notes, and architectural decisions from past development work.

## Contributing

Before contributing:

1. **Read the testing guide** - Ensure tests pass and coverage is maintained
2. **Follow existing patterns** - Review codebase structure in [CLAUDE.md](../../CLAUDE.md)
3. **Update documentation** - Add/update docs for any new features
4. **Run tests** - `pytest --cov=custom_components.battery_energy_trading --cov-fail-under=90`

## Quick Reference

### Development Commands

```bash
# Setup
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=custom_components.battery_energy_trading --cov-report=html

# Run specific test
pytest tests/test_energy_optimizer.py -v
```

### Project Structure

```
custom_components/battery_energy_trading/
├── __init__.py              # Integration setup
├── config_flow.py           # Configuration wizard
├── energy_optimizer.py      # Core optimization logic
├── sungrow_helper.py        # Sungrow auto-detection
├── sensor.py                # Sensor entities
├── binary_sensor.py         # Binary sensor entities
├── number.py                # Number configuration entities
└── switch.py                # Switch control entities
```

## Additional Resources

- **[CLAUDE.md](../../CLAUDE.md)** - AI assistant guidelines and architecture documentation
- **[API Documentation](../api/)** - API reference (coming soon)
- **[Integration Guides](../integrations/)** - Third-party integration documentation
