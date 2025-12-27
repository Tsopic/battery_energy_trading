# Shared Task Notes - Battery Energy Trading

## Current State (2025-12-27)

- **All 258 tests passing** in ~1s
- **Coverage: 90.55%** (meets 90% threshold)
- **Branch**: `continuous-claude/iteration-3/2025-12-27-d4ab4dde`

## Primary Goal

Investigate the code repo, make sure it works with Battery, Home Assistant and Sungrow inverter. Improve test coverage and Nord Pool price data handling.

## Priority Work: energy_optimizer.py Coverage (83.58%)

The main coverage gap is in `energy_optimizer.py`. Here are the **specific uncovered lines** from the coverage report:

### Lines to Cover (49 missed statements, 31 partial branches)

| Lines | Function | What's Missing |
|-------|----------|----------------|
| 59-64 | `_clean_expired_cache` | Cache cleanup when entries expire |
| 107, 110->114 | `_merge_price_data` | Tomorrow data filtering with overlap |
| 127 | `_normalize_datetime_key` | Timezone-aware datetime handling |
| 150-152 | `_create_normalized_solar_dict` | Datetime object key parsing |
| 169 | `_calculate_slot_duration` | Single-price edge case |
| 192, 200-201 | `_estimate_solar_impact` | Empty wh_hours, debug logging |
| 219-225, 230, 238-240 | `_estimate_solar_impact` | Solar calculation edge cases, exception handling |
| 261 | `_calculate_solar_between_slots` | No wh_hours in forecast |
| 506-507 | `select_discharge_slots` | Empty feasible slots after projection |
| 571, 579->566 | `select_discharge_slots` | Solar battery level fallback |
| 666, 669-670, 674-675 | `select_charging_slots` | Empty price data, multi-day logging |
| 687-691, 704-716 | `select_charging_slots` | Solar reduces charging need |
| 735-738, 758, 768->765 | `select_charging_slots` | Invalid charge rate, max_slots limit |
| 833 | `calculate_arbitrage_opportunities` | Insufficient price data |
| 913 | `is_current_slot_selected` | Timezone conversion edge case |
| 968->973, 1008->1029 | `_combine_consecutive_slots` | Single slot groups |
| 1012->1029, 1041, 1073->1091 | `_merge_slot_group` | Partial discharge with battery reserve |

### Suggested Test Cases to Add

1. **Cache expiration test** - Test `_clean_expired_cache` with expired entries
2. **Multi-day merge with overlap** - Test `_merge_price_data` when tomorrow has overlapping data
3. **Timezone-aware datetime test** - Test datetime normalization with timezone
4. **Solar forecast with datetime keys** - Test parsing datetime objects (not just strings)
5. **Single price slot** - Test when only one price entry exists
6. **Empty solar forecast** - Test `wh_hours: {}` case
7. **Solar exception handling** - Test malformed solar data
8. **No feasible slots after projection** - Test when all slots fail projection
9. **Solar reduces charging to zero** - Test when solar covers full target
10. **Partial discharge respecting reserve** - Test min_battery_reserve_percent

## Commands

```bash
# Run tests
source .venv-py313/bin/activate && pytest tests/

# Run with coverage
pytest --cov=custom_components.battery_energy_trading --cov-report=term-missing tests/

# Run specific test file
pytest tests/test_energy_optimizer.py -v

# Format code before commit
ruff format custom_components/battery_energy_trading/
```

## Git Workflow

```bash
# Stage and commit
git add .
git commit -m "test: add coverage for energy_optimizer edge cases"
```

## Files of Interest

- `custom_components/battery_energy_trading/energy_optimizer.py` - Core optimization logic
- `tests/test_energy_optimizer.py` - Main test file to expand
- `tests/conftest.py` - Shared pytest fixtures

## Notes

- Use `.venv-py313` Python environment (Python 3.13)
- Coverage threshold is 90% - currently at 90.55%
- No ROADMAP.md or PHILOSOPHY.md files exist in the repo
- No `.claude/commands/` files configured yet
