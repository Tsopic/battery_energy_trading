# Shared Task Notes

## Current State (2025-12-27)

- **Tests**: 258 passing, ~2s execution
- **Coverage**: 90.55% overall (meets 90% requirement)
- **Branch**: `continuous-claude/iteration-2/2025-12-27-3f454a8f`

## Priority: Increase energy_optimizer.py Coverage (83.58%)

The `energy_optimizer.py` module is the core optimization engine but has the lowest coverage. Targeting these uncovered paths would push coverage higher.

### Key Uncovered Line Groups

| Lines | What's Not Covered |
|-------|-------------------|
| 59-64 | Cache expired, key deletion branch |
| 150-152 | Datetime key parsing (when key is already a datetime object) |
| 200-201 | Empty `wh_hours` log message |
| 219-225 | Solar estimation when `solar_wh > 0` (level increase calc) |
| 238-240 | Exception handling in `_estimate_solar_impact` |
| 506-507 | "No feasible slots after projection" log path |
| 666, 669-670, 674-675 | Charging multiday cache/empty price warnings |
| 687-691 | Solar estimates reduce charging need calculation |
| 704-716 | Solar contribution reduces needed energy branch |
| 735-738 | Zero charge rate warning |
| 1008-1029 | Partial discharge on single slot (reserve limit hit) |
| 1041 | Zero energy weighted price fallback |
| 1073-1091 | Partial discharge on combined period (reserve limit) |

### Suggested Tests to Add

1. **Cache expiration test**: Set short TTL, verify expired entries are deleted
2. **Solar forecast with datetime keys**: Test `_create_normalized_solar_dict` with actual `datetime` objects as keys
3. **Empty wh_hours**: Solar forecast with `wh_hours: {}`
4. **Solar estimation exception**: Mock an exception in `_estimate_solar_impact`
5. **Charging with multiday + solar**: Test `select_charging_slots` with solar forecast reducing need
6. **Partial discharge at reserve**: Create scenario where battery hits reserve mid-slot

## Technical Notes

### Nord Pool Price Format
```python
{
    "start": datetime,
    "end": datetime,
    "value": float  # EUR/kWh
}
```
Price data comes from `raw_today` and `raw_tomorrow` attributes on Nord Pool sensor.

### Solar Forecast Format
```python
{
    "wh_hours": {
        "2025-12-27T12:00:00": 1500.0,  # Wh per hour
        "2025-12-27T13:00:00": 2000.0,
        ...
    }
}
```
Keys can be ISO strings or datetime objects. Values are watt-hours.

### Slot Duration Detection
Optimizer auto-detects 15-min vs hourly slots by comparing consecutive `start` times.

## Commands

```bash
# Run tests with coverage
source .venv-py313/bin/activate && pytest tests/ --cov=custom_components.battery_energy_trading --cov-report=term-missing

# Run single test file
pytest tests/test_energy_optimizer.py -v

# Lint and format
ruff check --fix custom_components/battery_energy_trading/
ruff format custom_components/battery_energy_trading/
```

## Next Steps

1. Add tests for uncovered edge cases in energy_optimizer.py
2. Consider property-based testing for optimization algorithms (hypothesis library)
3. Real Nord Pool data validation with Estonian market patterns
