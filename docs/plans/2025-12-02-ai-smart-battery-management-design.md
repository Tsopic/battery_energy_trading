# AI Smart Battery Management Design

**Date:** 2025-12-02
**Status:** Design Phase
**Target Platform:** Raspberry Pi 4 (4GB RAM)

## Overview

Enhance the existing `battery_energy_trading` Home Assistant integration with AI/ML capabilities for:
1. **Solar Production Prediction** - Correct Forecast.Solar with local patterns
2. **Load Forecasting** - Predict household consumption including heat pump & AC
3. **Optimal Decision Making** - Q-learning agent for charge/discharge decisions

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Home Assistant (Raspberry Pi 4)                  │
├─────────────────────────────────────────────────────────────────────┤
│  battery_energy_trading integration                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AI Optimization Module                          │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐       │   │
│  │  │   Solar     │ │    Load     │ │   Decision      │       │   │
│  │  │  Predictor  │ │  Forecaster │ │   Optimizer     │       │   │
│  │  │  (Ensemble) │ │  (Ensemble) │ │   (Q-Learning)  │       │   │
│  │  └──────┬──────┘ └──────┬──────┘ └────────┬────────┘       │   │
│  │         └───────────────┼──────────────────┘                │   │
│  │                         ▼                                   │   │
│  │              ┌─────────────────────┐                        │   │
│  │              │  ONNX Runtime       │                        │   │
│  │              │  (Inference Engine) │                        │   │
│  │              └─────────────────────┘                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌───────────────────────────┼───────────────────────────────────┐ │
│  │           Existing Components                                  │ │
│  │  • Nord Pool Coordinator  • Energy Optimizer                   │ │
│  │  • Binary Sensors         • Automation Helper                  │ │
│  └────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

## Data Sources

### Available Entities (from Home Assistant)

#### Solar & PV System
| Entity | Type | Use |
|--------|------|-----|
| `sensor.total_dc_power` | Real-time W | Current solar output |
| `sensor.mppt1_power`, `sensor.mppt2_power` | Real-time W | Per-string output |
| `sensor.power_production_now` | Forecast.Solar | Estimated current |
| `sensor.energy_production_today` | Forecast.Solar | Today's forecast |
| `sensor.energy_production_tomorrow` | Forecast.Solar | Tomorrow's forecast |
| `sensor.daily_pv_generation` | Daily kWh | Actual daily production |
| `sensor.monthly_pv_generation_01-12` | Monthly kWh | Per-month history |
| `sensor.yearly_pv_generation_2019-2029` | Yearly kWh | 10 years history |

#### Battery System
| Entity | Type | Use |
|--------|------|-----|
| `sensor.battery_level` | % | Current SOC |
| `sensor.battery_capacity` | kWh | Total capacity |
| `sensor.battery_state_of_health` | % | Degradation tracking |
| `sensor.battery_charging_power` | W | Current charge rate |
| `sensor.battery_discharging_power` | W | Current discharge rate |
| `sensor.battery_temperature` | °C | Health monitoring |
| `sensor.daily_battery_charge` | kWh | Daily energy in |
| `sensor.daily_battery_discharge` | kWh | Daily energy out |

#### Load & Consumption
| Entity | Type | Use |
|--------|------|-----|
| `sensor.load_power` | Real-time W | Current house load |
| `sensor.total_active_power` | Real-time W | Total active power |
| `sensor.daily_consumed_energy` | Daily kWh | Daily consumption |
| `sensor.total_consumed_energy` | Cumulative kWh | Lifetime consumption |

#### Thermia Heat Pump (Major Load)
| Entity | Type | Use |
|--------|------|-----|
| `sensor.karksi_outdoor_temperature` | °C | Key predictor for HP load |
| `binary_sensor.karksi_3kw_power_status` | ON/OFF | 3kW stage active |
| `binary_sensor.karksi_6kw_power_status` | ON/OFF | 6kW stage active |
| `binary_sensor.karksi_9kw_power_status` | ON/OFF | 9kW stage active |
| `binary_sensor.karksi_12kw_power_status` | ON/OFF | 12kW stage active |
| `binary_sensor.karksi_15kw_power_status` | ON/OFF | 15kW stage active |
| `binary_sensor.karksi_compr_operational_status` | ON/OFF | Compressor running |
| `binary_sensor.karksi_heating_operational_status` | ON/OFF | Heating mode |
| `binary_sensor.karksi_hot_water_operational_status` | ON/OFF | Hot water mode |

#### Grid Exchange
| Entity | Type | Use |
|--------|------|-----|
| `sensor.import_power` | W | Current grid import |
| `sensor.export_power` | W | Current grid export |
| `sensor.daily_imported_energy` | kWh | Daily grid buy |
| `sensor.daily_exported_energy` | kWh | Daily grid sell |
| `sensor.daily_imported_energy_cost` | EUR | Daily buy cost |
| `sensor.daily_exported_energy_compensation` | EUR | Daily sell revenue |

#### Pricing
| Entity | Type | Use |
|--------|------|-----|
| `sensor.nordpool_kwh_ee_eur_3_10_022` | EUR/kWh | Estonian spot price |

#### Weather & Environment
| Entity | Type | Use |
|--------|------|-----|
| `weather.forecast_ainja_34` | Forecast | Weather conditions |
| `sensor.karksi_outdoor_temperature` | °C | Actual outdoor temp |
| `sensor.sun_next_rising/setting` | Timestamp | Solar timing |

### Data Storage

**Source:** Home Assistant Long-Term Statistics (recorder database)
- 5-minute resolution for recent data
- Hourly resolution for older data
- No additional database required

## Inverter Control

### Control Entities

The Sungrow inverter is controlled via Modbus through these entities:

```yaml
# EMS Mode Control
input_select.set_sg_ems_mode:
  options:
    - "Self-consumption"    # Normal operation
    - "Forced mode"         # Manual charge/discharge control
    - "External EMS mode"   # External control
    - "VPP mode"           # Virtual power plant

# Charge/Discharge Command
input_select.set_sg_battery_forced_charge_discharge_cmd:
  options:
    - "Stop (default)"      # No forced operation
    - "Forced charge"       # Force charging from grid
    - "Forced discharge"    # Force discharging to grid

# Power Level
input_number.set_sg_forced_charge_discharge_power:
  min: 0
  max: 10000
  unit: W
```

### Control Scripts (Available)

```yaml
script.sg_set_forced_charge_battery_mode:    # Sets forced charging
script.sg_set_forced_discharge_battery_mode: # Sets forced discharge
script.sg_set_self_consumption_mode:         # Returns to normal
script.sg_set_battery_bypass_mode:           # Battery bypass
script.sg_set_self_consumption_limited_discharge: # Limited discharge
```

### AI Control Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI DECISION → INVERTER CONTROL                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  AI Decision Engine                                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Inputs:                                                     │   │
│  │  • Predicted solar (next 24h)                               │   │
│  │  • Predicted load (next 24h, including heat pump)           │   │
│  │  • Nord Pool prices (today + tomorrow)                       │   │
│  │  • Current battery SOC                                       │   │
│  │  • Weather forecast                                          │   │
│  │                                                              │   │
│  │  Output: Optimal action for current 15-min slot              │   │
│  │  • CHARGE at X kW                                            │   │
│  │  • DISCHARGE at X kW                                         │   │
│  │  • HOLD (self-consumption)                                   │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│                             ▼                                       │
│  Control Execution                                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  IF action == CHARGE:                                        │   │
│  │    → input_select.set_sg_ems_mode = "Forced mode"           │   │
│  │    → input_select.set_sg_battery_forced_charge_discharge_cmd │   │
│  │      = "Forced charge"                                       │   │
│  │    → input_number.set_sg_forced_charge_discharge_power       │   │
│  │      = charge_power_watts                                    │   │
│  │                                                              │   │
│  │  IF action == DISCHARGE:                                     │   │
│  │    → input_select.set_sg_ems_mode = "Forced mode"           │   │
│  │    → input_select.set_sg_battery_forced_charge_discharge_cmd │   │
│  │      = "Forced discharge"                                    │   │
│  │    → input_number.set_sg_forced_charge_discharge_power       │   │
│  │      = discharge_power_watts                                 │   │
│  │                                                              │   │
│  │  IF action == HOLD:                                          │   │
│  │    → input_select.set_sg_ems_mode = "Self-consumption"      │   │
│  │    → input_select.set_sg_battery_forced_charge_discharge_cmd │   │
│  │      = "Stop (default)"                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Model Architecture

### 1. Solar Predictor (Correction Layer)

Since Forecast.Solar is already integrated, we build a **correction model** rather than predicting from scratch:

```
Input Features:
├── Forecast.Solar prediction (kWh)
├── Recent forecast error (last 7 days MAPE)
├── Weather: cloud cover, temperature
├── Time: hour, day of year, is_weekend
└── Historical: actual vs forecast ratio at same time

Model: Gradient Boosting (XGBoost) - small ensemble
Output: Correction factor (multiply Forecast.Solar by this)

Example:
  Forecast.Solar says: 5.2 kWh
  Model correction: 0.92 (learned your panels underperform in morning)
  Corrected prediction: 4.78 kWh
```

### 2. Load Forecaster (with Heat Pump)

```
Input Features:
├── Time: hour, day_of_week, is_weekend, is_holiday, month
├── Temperature: outdoor (from heat pump sensor)
├── Heat pump state: which power stage was active at similar temps
├── Historical: load at same hour (t-24h, t-168h)
├── Rolling averages: 4h, 24h load averages
└── Weather: temperature forecast

Model: Ensemble of Gradient Boosting + Simple time-series

Heat Pump Load Prediction (discrete stages):
┌─────────────────────────────────────────────┐
│ Outdoor Temp  →  Predicted HP Power Stage   │
├─────────────────────────────────────────────┤
│ > 15°C        →  0 kW (off)                 │
│ 10-15°C       →  3 kW                       │
│ 5-10°C        →  6 kW                       │
│ 0-5°C         →  9 kW                       │
│ -5-0°C        →  12 kW                      │
│ < -5°C        →  15 kW                      │
└─────────────────────────────────────────────┘

Total Load = Base Load + Heat Pump + Variable Loads
```

### 3. Decision Optimizer (Q-Learning)

**CRITICAL: Nord Pool Prices are PRIMARY Decision Driver**

The AI does NOT replace price-based decision making. Nord Pool day-ahead prices (available after 13:00 CET) provide the foundation:

```
Decision Hierarchy:
1. Nord Pool prices (PRIMARY) - When to buy/sell based on actual market prices
2. AI solar forecast - How much battery capacity will solar provide?
3. AI load forecast - How much battery capacity will house need?
4. Q-learning optimizer - Fine-tune timing within price-selected windows
```

```
State Space (discretized for memory efficiency):
├── Battery SOC: 5 levels (0-20%, 20-40%, 40-60%, 60-80%, 80-100%)
├── Current price: 5 levels (very low, low, medium, high, very high) ⭐ PRIMARY
├── Next 6h prices: from Nord Pool raw_today/raw_tomorrow ⭐ PRIMARY
├── Price trend: 3 levels (rising, stable, falling)
├── Solar forecast: 4 levels (none, low, medium, high)
├── Load forecast: 3 levels (low, medium, high)
├── Net energy forecast: solar - load (surplus/deficit)
└── Hour of day: 6 periods (night, morning, midday, afternoon, evening, late)

Action Space:
├── CHARGE_HIGH (max rate) - only when price < threshold
├── CHARGE_LOW (half rate) - moderate price opportunity
├── HOLD (self-consumption) - default mode
├── DISCHARGE_LOW (half rate) - good price opportunity
└── DISCHARGE_HIGH (max rate) - only when price > threshold

Reward Function:
R = (revenue_from_discharge × actual_price)  ⭐ Price-weighted
    - (cost_of_charge × actual_price)        ⭐ Price-weighted
    - battery_cycle_penalty
    - grid_dependency_penalty
    + solar_utilization_bonus
```

**How AI Enhances Price-Based Decisions:**

```
Example: Nord Pool shows high prices at 17:00-19:00

Without AI (current system):
  → Discharge during 17:00-19:00 at max rate
  → May run out of battery before 19:00

With AI:
  → Predict: Solar will produce 2kWh during 15:00-17:00
  → Predict: Load will be 4kW at 18:00 (heat pump peak)
  → Decision: Start discharge at 17:30 (after solar covers early evening)
  → Decision: Reserve 2kWh for heat pump spike at 18:00
  → Result: More revenue, better battery utilization
```

## Training Pipeline

### Automatic Training Schedule

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AUTOMATIC TRAINING PIPELINE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TRIGGER: Every Sunday at 03:00 (low activity period)               │
│                                                                     │
│  STEP 1: Data Extraction (async, ~5 minutes)                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • Query HA Long-Term Statistics for last 90 days           │   │
│  │  • Extract: solar, load, battery, prices, temperatures      │   │
│  │  • Align timestamps, handle missing data                    │   │
│  │  • Save to temporary training dataset                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  STEP 2: Feature Engineering (~2 minutes)                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • Create time features (hour, day, month, is_weekend)      │   │
│  │  • Calculate lag features (t-1h, t-24h, t-168h)             │   │
│  │  • Compute rolling averages (4h, 24h, 7d)                   │   │
│  │  • Add weather correlations                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  STEP 3: Model Training (sequential to limit RAM, ~30-60 min)       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  3a. Train Solar Corrector                                  │   │
│  │      • Load: ~300MB RAM                                     │   │
│  │      • Time: ~10 minutes                                    │   │
│  │      • Free memory before next                              │   │
│  │                                                             │   │
│  │  3b. Train Load Forecaster                                  │   │
│  │      • Load: ~400MB RAM                                     │   │
│  │      • Time: ~15 minutes                                    │   │
│  │      • Free memory before next                              │   │
│  │                                                             │   │
│  │  3c. Update Q-Learning Agent                                │   │
│  │      • Load: ~200MB RAM                                     │   │
│  │      • Time: ~10 minutes                                    │   │
│  │      • Incremental update, not full retrain                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  STEP 4: Model Export (~1 minute)                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • Convert models to ONNX format                            │   │
│  │  • Validate model outputs                                   │   │
│  │  • Save with timestamp version                              │   │
│  │  • Keep last 3 versions for rollback                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  STEP 5: Hot Reload (~immediate)                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  • Load new models into ONNX Runtime                        │   │
│  │  • Verify inference works                                   │   │
│  │  • Fire event: battery_energy_trading_ai_trained            │   │
│  │  • Log training metrics                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  FALLBACK:                                                          │
│  • If training fails → keep existing models                        │
│  • If inference fails → fall back to rule-based optimizer          │
│  • Alert via persistent notification                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Training Configuration

```yaml
# AI training configuration (config entry options)
ai_training:
  enabled: true
  schedule: "0 3 * * 0"  # Every Sunday at 03:00
  data_days: 90          # Days of historical data to use
  min_data_days: 30      # Minimum data required to train
  max_training_time: 3600  # Max 1 hour, abort if exceeded

  solar_model:
    type: "gradient_boosting"
    n_estimators: 50
    max_depth: 5

  load_model:
    type: "ensemble"
    models: ["gradient_boosting", "ridge_regression"]

  decision_model:
    type: "q_learning"
    learning_rate: 0.1
    discount_factor: 0.95
    exploration_rate: 0.1
```

## Module Structure

```
custom_components/battery_energy_trading/
├── __init__.py                    # Add AI initialization
├── energy_optimizer.py            # Keep as fallback
├── coordinator.py                 # Add AI predictions to data
│
├── ai/                            # NEW - AI Module
│   ├── __init__.py
│   ├── config.py                  # Entity mappings, training config
│   ├── data_extractor.py          # Query HA Long-Term Statistics
│   ├── feature_engineering.py     # Transform raw → ML features
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py               # Base model interface
│   │   ├── solar_predictor.py    # Solar correction ensemble
│   │   ├── load_forecaster.py    # Load prediction ensemble
│   │   └── decision_optimizer.py # Q-learning agent
│   │
│   ├── training/
│   │   ├── __init__.py
│   │   ├── trainer.py            # Training orchestration
│   │   ├── scheduler.py          # Automatic weekly training
│   │   └── evaluator.py          # Model performance metrics
│   │
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── predictor.py          # ONNX runtime inference
│   │   └── controller.py         # Execute decisions on inverter
│   │
│   └── energy_optimizer_ai.py    # Enhanced optimizer with AI
│
├── sensor.py                      # Add AI prediction sensors
├── services.yaml                  # Add AI services
└── strings.json                   # Add AI-related translations
```

## New Sensors

```yaml
# AI Prediction Sensors
sensor.battery_energy_trading_ai_recommendation:
  state: "DISCHARGE"  # or "CHARGE", "HOLD"
  attributes:
    confidence: 0.87
    reasoning: "High price (0.35 EUR), low solar forecast, sufficient battery"
    solar_forecast_24h: [0.1, 0.5, 2.1, 3.4, ...]
    load_forecast_24h: [1.2, 1.8, 2.5, 3.1, ...]

sensor.battery_energy_trading_ai_status:
  state: "Ready"  # or "Training", "Error", "Initializing"
  attributes:
    last_training: "2025-12-01T03:00:00"
    model_version: "2025-12-01-v1"
    solar_accuracy_7d: 0.92
    load_accuracy_7d: 0.88
    decisions_today: 12
    successful_decisions: 11
```

## New Services

```yaml
battery_energy_trading.train_ai_models:
  name: Train AI Models
  description: Manually trigger AI model training
  fields:
    days_of_data:
      description: Days of historical data (default: 90)
      default: 90
      selector:
        number:
          min: 30
          max: 365

battery_energy_trading.get_ai_prediction:
  name: Get AI Prediction
  description: Get current AI recommendation with explanation

battery_energy_trading.set_ai_mode:
  name: Set AI Mode
  description: Enable/disable AI-driven decisions
  fields:
    enabled:
      description: Enable AI mode
      selector:
        boolean:

battery_energy_trading.reset_ai_models:
  name: Reset AI Models
  description: Clear trained models and start fresh
```

## Memory Footprint (Raspberry Pi 4GB)

| Component | Training RAM | Inference RAM | Disk |
|-----------|-------------|---------------|------|
| Data Extraction | ~200MB | - | - |
| Feature Engineering | ~100MB | - | - |
| Solar Model Training | ~300MB | - | - |
| Load Model Training | ~400MB | - | - |
| Q-Learning Update | ~200MB | - | - |
| **Training Peak** | **~500MB** | - | - |
| | | | |
| Solar Model Inference | - | ~30MB | ~3MB |
| Load Model Inference | - | ~30MB | ~3MB |
| Q-Learning Inference | - | ~20MB | ~2MB |
| ONNX Runtime | - | ~100MB | - |
| **Inference Total** | - | **~180MB** | **~8MB** |

**Conclusion:** Fits comfortably on Pi 4GB. Training runs sequentially at ~500MB peak. Inference uses ~180MB alongside Home Assistant.

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Create `ai/` module structure
- [ ] Implement `data_extractor.py` - query HA statistics
- [ ] Implement `feature_engineering.py` - basic features
- [ ] Add configuration for entity mappings
- [ ] Unit tests for data extraction

### Phase 2: Solar Predictor (Week 3-4)
- [ ] Implement `solar_predictor.py` - correction model
- [ ] Train on historical data (Forecast.Solar vs actual)
- [ ] Export to ONNX
- [ ] Add `sensor.battery_energy_trading_ai_solar_forecast`
- [ ] Validate predictions against actuals

### Phase 3: Load Forecaster (Week 5-6)
- [ ] Implement `load_forecaster.py` - with heat pump modeling
- [ ] Add temperature correlation features
- [ ] Train on historical load data
- [ ] Export to ONNX
- [ ] Add `sensor.battery_energy_trading_ai_load_forecast`

### Phase 4: Decision Optimizer (Week 7-8)
- [ ] Implement `decision_optimizer.py` - Q-learning agent
- [ ] Define state/action spaces
- [ ] Implement reward calculation from historical data
- [ ] Train initial agent
- [ ] Add `sensor.battery_energy_trading_ai_recommendation`

### Phase 5: Control Integration (Week 9-10)
- [ ] Implement `controller.py` - execute AI decisions
- [ ] Map AI actions to Sungrow control entities
- [ ] Add safety checks and rate limiting
- [ ] Implement fallback to rule-based optimizer
- [ ] End-to-end testing

### Phase 6: Automatic Training (Week 11-12)
- [ ] Implement `scheduler.py` - weekly training automation
- [ ] Add training status sensor
- [ ] Implement model versioning and rollback
- [ ] Add services for manual training control
- [ ] Documentation and user guide

## Success Criteria

1. **Solar Prediction**: Within 15% of actual (MAPE < 0.15)
2. **Load Prediction**: Within 20% of actual (MAPE < 0.20)
3. **Cost Savings**: 10%+ improvement over rule-based optimizer
4. **Reliability**: < 1% decision failures
5. **Performance**: Training completes in < 1 hour on Pi 4
6. **Memory**: Peak RAM usage < 1GB during training

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Training too slow on Pi | Train models sequentially, limit complexity |
| Insufficient historical data | Require 30+ days before enabling AI mode |
| Bad predictions harm battery | Always allow fallback to rule-based, safety limits |
| Model drift over time | Weekly automatic retraining |
| Pi runs out of memory | Sequential training, explicit garbage collection |

## References

- Existing `energy_optimizer.py` - rule-based optimization
- Existing `automation_helper.py` - inverter control templates
- Sungrow Modbus control via `input_select`/`input_number` entities
- Home Assistant Long-Term Statistics API
- scikit-learn, XGBoost for models
- ONNX Runtime for inference
