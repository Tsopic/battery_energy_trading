# Codebase Coherence Review Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Review and fix all coherence issues in the Battery Energy Trading codebase to ensure entity IDs, naming conventions, tests, and documentation are consistent.

**Architecture:** Systematic review of entity naming (const.py vs actual names), dashboard bindings, test coverage for new AI modules, and CLAUDE.md documentation accuracy.

**Tech Stack:** Python 3.11+, Home Assistant, pytest, ruff

---

## Task 1: Audit Entity ID Generation Pattern

**Files:**
- Review: `custom_components/battery_energy_trading/base_entity.py`
- Review: `custom_components/battery_energy_trading/const.py`
- Review: `custom_components/battery_energy_trading/number.py`
- Review: `custom_components/battery_energy_trading/switch.py`
- Review: `custom_components/battery_energy_trading/binary_sensor.py`
- Review: `custom_components/battery_energy_trading/sensor.py`

**Step 1: Document current entity ID pattern**

The codebase uses `_attr_has_entity_name = True` in base_entity.py:50, which means:
- Entity ID = slugify(device_name + " " + friendly_name)
- Device name = "Battery Energy Trading"
- Result: `{domain}.battery_energy_trading_{slugified_friendly_name}`

**Current Entity ID Mapping:**

| Const Key | Friendly Name | Generated Entity ID |
|-----------|---------------|---------------------|
| `NUMBER_MIN_BATTERY_LEVEL` | "Minimum Battery Discharge Level" | `number.battery_energy_trading_minimum_battery_discharge_level` |
| `NUMBER_DISCHARGE_RATE_KW` | "Battery Discharge Rate" | `number.battery_energy_trading_battery_discharge_rate` |
| `BINARY_SENSOR_BATTERY_LOW` | "Battery Low" | `binary_sensor.battery_energy_trading_battery_low` → BUT user shows `battery_below_15` |

**Issue Found:** User's actual entity `binary_sensor.battery_energy_trading_battery_below_15` doesn't match expected `battery_low`. This suggests code changed but entity registry retained old names.

**Step 2: Decision point - Keep current pattern or standardize**

Options:
1. **Keep current pattern** - Dashboard uses actual HA-generated entity IDs (done in previous commit)
2. **Force short entity IDs** - Remove `_attr_has_entity_name=True` and use `_attr_suggested_object_id`

Recommend: Keep current pattern for backward compatibility.

---

## Task 2: Verify All Sensor Attributes Match Dashboard

**Files:**
- Review: `dashboards/battery_energy_trading_dashboard.yaml`
- Review: `custom_components/battery_energy_trading/sensor.py`

**Step 1: Check DischargeHoursSensor attributes**

Dashboard expects:
```yaml
- type: attribute
  entity: sensor.battery_energy_trading_discharge_time_slots
  attribute: slot_count
  attribute: total_energy_kwh
  attribute: estimated_revenue_eur
  attribute: average_price
  attribute: slots  # For slot iteration
```

Code provides (sensor.py:350-480):
```python
@property
def extra_state_attributes(self) -> dict[str, Any]:
    return {
        "slot_count": ...,
        "total_energy_kwh": ...,
        "estimated_revenue_eur": ...,
        "average_price": ...,
        "slots": [...],
        ...
    }
```

**Status:** VERIFIED - All attributes match

**Step 2: Check ChargingHoursSensor attributes**

Dashboard expects:
```yaml
- type: attribute
  entity: sensor.battery_energy_trading_charging_time_slots
  attribute: slot_count
  attribute: total_energy_kwh
  attribute: estimated_cost_eur
  attribute: average_price
```

**Status:** VERIFIED - All attributes match

**Step 3: Check ArbitrageOpportunitiesSensor attributes**

Dashboard expects:
```yaml
attribute: opportunities_count
attribute: best_profit
attribute: best_roi
attribute: all_opportunities
```

**Status:** VERIFIED - All attributes match

---

## Task 3: Verify New AI Module Integration

**Files:**
- Review: `custom_components/battery_energy_trading/ai/__init__.py`
- Review: `custom_components/battery_energy_trading/__init__.py`
- Review: `tests/test_trainer.py`

**Step 1: Verify AI module exports**

```python
# ai/__init__.py should export:
from .config import AIConfig
from .data_extractor import DataExtractor
from .feature_engineering import FeatureEngineering, create_time_features, ...
from .models import Action, BaseModel, DecisionOptimizer, LoadForecaster, SolarPredictor
from .training import AITrainer
```

Run: `python -c "from custom_components.battery_energy_trading.ai import AITrainer, AIConfig, DecisionOptimizer; print('OK')"`

**Step 2: Verify AI services registered**

```python
# __init__.py should register:
# - train_ai_models
# - get_ai_prediction
# - set_ai_mode
```

Run: `grep -n "async_register.*train_ai_models\|get_ai_prediction\|set_ai_mode" custom_components/battery_energy_trading/__init__.py`

**Step 3: Verify AI status sensor created**

```python
# sensor.py async_setup_entry should include:
AIStatusSensor(hass, entry, coordinator, nordpool_entity, ai_trainer)
```

Run: `grep -n "AIStatusSensor" custom_components/battery_energy_trading/sensor.py`

---

## Task 4: Update CLAUDE.md Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add AI module documentation**

Add new section after "### DataUpdateCoordinator Pattern":

```markdown
### AI Module (`ai/`)

The AI subsystem provides smart battery management using machine learning:

**Components:**
- `config.py` - AIConfig dataclass for entity mappings
- `data_extractor.py` - Extract training data from HA Long-Term Statistics
- `feature_engineering.py` - Create time, lag, and rolling features
- `models/` - ML model implementations:
  - `base.py` - Abstract BaseModel interface
  - `solar_predictor.py` - GradientBoosting correction for Forecast.Solar
  - `load_forecaster.py` - Ensemble model for load prediction
  - `decision_optimizer.py` - Q-learning with epsilon-greedy policy
- `training/trainer.py` - Sequential training orchestrator (Pi 4 compatible)

**Services:**
- `train_ai_models` - Trigger model training from historical data
- `get_ai_prediction` - Get current AI recommendation (CHARGE/DISCHARGE/HOLD)
- `set_ai_mode` - Enable/disable AI-driven decisions

**Memory Management:**
Sequential training with gc.collect() between models to stay under 500MB peak.
```

**Step 2: Update Entity documentation**

Add to "Sensor Entities" section:
```markdown
- `sensor.battery_energy_trading_ai_status` (v0.16.0) - AI system status
  - States: `Not Configured`, `Training`, `Ready`, `Initializing`
  - Attributes: `last_training`, `solar_model_trained`, `load_model_trained`,
    `decision_model_trained`, `training_metrics`
```

**Step 3: Update Dashboard section**

Add to Dashboard Features:
```markdown
6. **AI Status** (v0.16.0) - Shows AI training status, model readiness, and training button
```

---

## Task 5: Add Missing Tests for AI Integration

**Files:**
- Create/Modify: `tests/test_init.py`

**Step 1: Write test for AI trainer initialization**

```python
async def test_ai_trainer_initialized_on_setup(mock_hass, mock_config_entry):
    """Test that AI trainer is initialized during setup."""
    await async_setup_entry(mock_hass, mock_config_entry)

    entry_data = mock_hass.data[DOMAIN][mock_config_entry.entry_id]
    assert "ai_trainer" in entry_data
    assert entry_data["ai_trainer"] is not None
```

**Step 2: Run test**

Run: `pytest tests/test_init.py -v -k ai_trainer`

---

## Task 6: Verify services.yaml Completeness

**Files:**
- Review: `custom_components/battery_energy_trading/services.yaml`

**Step 1: Verify all services documented**

Services should include:
- `sync_sungrow_parameters`
- `generate_automation_scripts`
- `force_refresh`
- `train_ai_models`
- `get_ai_prediction`
- `set_ai_mode`

Run: `grep "^[a-z_]*:" custom_components/battery_energy_trading/services.yaml`

**Step 2: Verify service schemas match code**

Each service in services.yaml should have matching fields in __init__.py handler.

---

## Task 7: Final Coherence Verification

**Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: All tests pass

**Step 2: Run linting**

```bash
ruff check custom_components/battery_energy_trading/
ruff format --check custom_components/battery_energy_trading/
```
Expected: No issues

**Step 3: Verify dashboard loads without errors**

Manual test: Import dashboard YAML into Home Assistant and verify no "entity not found" warnings.

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "docs: update CLAUDE.md with AI module documentation"
```

---

## Summary Checklist

- [x] Entity ID pattern documented and consistent
- [x] Dashboard entity IDs match actual HA entities
- [x] Sensor attributes match dashboard expectations
- [x] AI module properly integrated and exported
- [x] CLAUDE.md updated with AI documentation
- [x] All tests passing (363 tests)
- [x] Linting clean
- [x] services.yaml complete (6 services)

**Completed:** 2025-12-02

