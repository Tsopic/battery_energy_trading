# AI Smart Battery Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance battery_energy_trading with AI/ML capabilities for solar prediction, load forecasting, and Q-learning optimization on Raspberry Pi 4.

**Architecture:** Modular AI components in `ai/` subdirectory. ONNX Runtime for inference (~180MB), sequential training (~500MB peak). Nord Pool prices remain PRIMARY decision driver; AI enhances timing within price windows.

**Tech Stack:** scikit-learn, XGBoost, ONNX Runtime, Home Assistant Long-Term Statistics API, asyncio

---

## Pre-Implementation Setup

### Task 0: Add AI Dependencies

**Files:**
- Modify: `custom_components/battery_energy_trading/manifest.json`

**Step 1: Update manifest with AI dependencies**

```json
{
  "domain": "battery_energy_trading",
  "name": "Battery Energy Trading",
  "version": "0.16.0",
  "documentation": "https://github.com/Tsopic/battery_energy_trading",
  "issue_tracker": "https://github.com/Tsopic/battery_energy_trading/issues",
  "requirements": [
    "onnxruntime>=1.16.0",
    "scikit-learn>=1.3.0",
    "xgboost>=2.0.0"
  ],
  "codeowners": ["@Tsopic"],
  "config_flow": true,
  "iot_class": "cloud_polling",
  "quality_scale": "silver"
}
```

**Step 2: Commit**

```bash
git add custom_components/battery_energy_trading/manifest.json
git commit -m "chore: add AI dependencies to manifest"
```

---

## Phase 1: Foundation (Data Extraction & Feature Engineering)

### Task 1.1: Create AI Module Structure

**Files:**
- Create: `custom_components/battery_energy_trading/ai/__init__.py`
- Create: `custom_components/battery_energy_trading/ai/config.py`

**Step 1: Create AI module init**

```python
"""AI module for smart battery management."""
from __future__ import annotations

__all__ = ["AIConfig", "DataExtractor", "FeatureEngineering"]
```

**Step 2: Create config with entity mappings**

```python
"""AI configuration and entity mappings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIConfig:
    """Configuration for AI models."""

    # Entity IDs (from Home Assistant)
    solar_power_entity: str = "sensor.total_dc_power"
    solar_forecast_entity: str = "sensor.energy_production_today"
    load_power_entity: str = "sensor.load_power"
    battery_level_entity: str = "sensor.battery_level"
    battery_capacity_entity: str = "sensor.battery_capacity"
    nordpool_entity: str = "sensor.nordpool_kwh_ee_eur_3_10_022"
    outdoor_temp_entity: str = "sensor.karksi_outdoor_temperature"

    # Heat pump power stage entities
    heat_pump_entities: dict[str, str] = field(default_factory=lambda: {
        "3kw": "binary_sensor.karksi_3kw_power_status",
        "6kw": "binary_sensor.karksi_6kw_power_status",
        "9kw": "binary_sensor.karksi_9kw_power_status",
        "12kw": "binary_sensor.karksi_12kw_power_status",
        "15kw": "binary_sensor.karksi_15kw_power_status",
    })

    # Training configuration
    training_days: int = 90
    min_training_days: int = 30
    training_schedule: str = "0 3 * * 0"  # Sunday 03:00

    # Model configuration
    solar_model_estimators: int = 50
    solar_model_max_depth: int = 5
    load_model_estimators: int = 50
    q_learning_rate: float = 0.1
    q_discount_factor: float = 0.95
    q_exploration_rate: float = 0.1

    @classmethod
    def from_config_entry(cls, entry_data: dict[str, Any]) -> "AIConfig":
        """Create config from Home Assistant config entry."""
        return cls(
            solar_power_entity=entry_data.get("solar_power_entity", cls.solar_power_entity),
            nordpool_entity=entry_data.get("nordpool_entity", cls.nordpool_entity),
            battery_level_entity=entry_data.get("battery_level_entity", cls.battery_level_entity),
            battery_capacity_entity=entry_data.get("battery_capacity_entity", cls.battery_capacity_entity),
        )
```

**Step 3: Create test file**

Create: `tests/test_ai_config.py`

```python
"""Tests for AI configuration."""
import pytest

from custom_components.battery_energy_trading.ai.config import AIConfig


class TestAIConfig:
    """Test AI configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = AIConfig()
        assert config.solar_power_entity == "sensor.total_dc_power"
        assert config.training_days == 90
        assert config.min_training_days == 30

    def test_from_config_entry(self) -> None:
        """Test creating config from entry data."""
        entry_data = {
            "nordpool_entity": "sensor.custom_nordpool",
            "battery_level_entity": "sensor.custom_battery",
        }
        config = AIConfig.from_config_entry(entry_data)
        assert config.nordpool_entity == "sensor.custom_nordpool"
        assert config.battery_level_entity == "sensor.custom_battery"
        # Defaults should still work
        assert config.solar_power_entity == "sensor.total_dc_power"

    def test_heat_pump_entities(self) -> None:
        """Test heat pump entity mappings."""
        config = AIConfig()
        assert "3kw" in config.heat_pump_entities
        assert "15kw" in config.heat_pump_entities
        assert config.heat_pump_entities["9kw"] == "binary_sensor.karksi_9kw_power_status"
```

**Step 4: Run tests**

```bash
pytest tests/test_ai_config.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/battery_energy_trading/ai/ tests/test_ai_config.py
git commit -m "feat(ai): add AI module structure and configuration"
```

---

### Task 1.2: Implement Data Extractor

**Files:**
- Create: `custom_components/battery_energy_trading/ai/data_extractor.py`
- Create: `tests/test_data_extractor.py`

**Step 1: Write failing test**

```python
"""Tests for data extraction from Home Assistant statistics."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.battery_energy_trading.ai.data_extractor import DataExtractor
from custom_components.battery_energy_trading.ai.config import AIConfig


class TestDataExtractor:
    """Test data extraction."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.data = {}
        return hass

    @pytest.fixture
    def config(self) -> AIConfig:
        """Create test config."""
        return AIConfig()

    @pytest.fixture
    def extractor(self, mock_hass: MagicMock, config: AIConfig) -> DataExtractor:
        """Create data extractor."""
        return DataExtractor(mock_hass, config)

    def test_init(self, extractor: DataExtractor, config: AIConfig) -> None:
        """Test extractor initialization."""
        assert extractor.config == config
        assert extractor.hass is not None

    @pytest.mark.asyncio
    async def test_get_statistics_entities(self, extractor: DataExtractor) -> None:
        """Test getting list of entities to query."""
        entities = extractor.get_statistics_entities()
        assert "sensor.total_dc_power" in entities
        assert "sensor.load_power" in entities
        assert "sensor.battery_level" in entities

    @pytest.mark.asyncio
    async def test_extract_training_data_empty(
        self, extractor: DataExtractor, mock_hass: MagicMock
    ) -> None:
        """Test extraction when no statistics available."""
        with patch(
            "custom_components.battery_energy_trading.ai.data_extractor.get_instance",
            return_value=MagicMock(async_add_executor_job=AsyncMock(return_value={})),
        ):
            data = await extractor.extract_training_data(days=7)
            assert data is not None
            assert len(data) == 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_data_extractor.py -v
```
Expected: FAIL (module not found)

**Step 3: Implement data extractor**

```python
"""Extract training data from Home Assistant Long-Term Statistics."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    statistics_during_period,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .config import AIConfig

_LOGGER = logging.getLogger(__name__)


class DataExtractor:
    """Extract training data from Home Assistant statistics."""

    def __init__(self, hass: HomeAssistant, config: AIConfig) -> None:
        """Initialize data extractor."""
        self.hass = hass
        self.config = config

    def get_statistics_entities(self) -> list[str]:
        """Get list of entity IDs to query for statistics."""
        entities = [
            self.config.solar_power_entity,
            self.config.solar_forecast_entity,
            self.config.load_power_entity,
            self.config.battery_level_entity,
            self.config.outdoor_temp_entity,
        ]
        # Add heat pump entities
        entities.extend(self.config.heat_pump_entities.values())
        return entities

    async def extract_training_data(
        self,
        days: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Extract training data from HA Long-Term Statistics.

        Args:
            days: Number of days of data to extract (default: config.training_days)
            start_time: Optional start time override
            end_time: Optional end time override

        Returns:
            Dictionary mapping entity_id to list of statistic records
        """
        if days is None:
            days = self.config.training_days

        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=days)

        entities = self.get_statistics_entities()

        try:
            instance = get_instance(self.hass)
            statistics = await instance.async_add_executor_job(
                self._get_statistics,
                start_time,
                end_time,
                entities,
            )
            return statistics
        except Exception as err:
            _LOGGER.error("Failed to extract training data: %s", err)
            return {}

    def _get_statistics(
        self,
        start_time: datetime,
        end_time: datetime,
        entities: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Get statistics from recorder (runs in executor)."""
        return statistics_during_period(
            self.hass,
            start_time,
            end_time,
            statistic_ids=entities,
            period="hour",
            units=None,
            types={"mean", "sum"},
        )

    async def extract_recent_data(
        self, hours: int = 24
    ) -> dict[str, list[dict[str, Any]]]:
        """Extract recent data for inference.

        Args:
            hours: Number of hours of recent data

        Returns:
            Dictionary mapping entity_id to list of recent records
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        try:
            instance = get_instance(self.hass)
            statistics = await instance.async_add_executor_job(
                self._get_statistics,
                start_time,
                end_time,
                self.get_statistics_entities(),
            )
            return statistics
        except Exception as err:
            _LOGGER.error("Failed to extract recent data: %s", err)
            return {}

    def has_sufficient_data(self, data: dict[str, list[dict[str, Any]]]) -> bool:
        """Check if extracted data is sufficient for training.

        Args:
            data: Extracted statistics data

        Returns:
            True if data meets minimum requirements
        """
        if not data:
            return False

        min_records = self.config.min_training_days * 24  # hourly data

        # Check key entities have enough data
        key_entities = [
            self.config.solar_power_entity,
            self.config.load_power_entity,
            self.config.battery_level_entity,
        ]

        for entity in key_entities:
            if entity not in data:
                _LOGGER.warning("Missing data for %s", entity)
                return False
            if len(data[entity]) < min_records:
                _LOGGER.warning(
                    "Insufficient data for %s: %d records (need %d)",
                    entity,
                    len(data[entity]),
                    min_records,
                )
                return False

        return True
```

**Step 4: Run tests**

```bash
pytest tests/test_data_extractor.py -v
```
Expected: PASS

**Step 5: Add more comprehensive tests**

Add to `tests/test_data_extractor.py`:

```python
    @pytest.mark.asyncio
    async def test_has_sufficient_data_true(self, extractor: DataExtractor) -> None:
        """Test sufficient data check passes with enough records."""
        # 30 days * 24 hours = 720 minimum records
        data = {
            "sensor.total_dc_power": [{"mean": 100}] * 800,
            "sensor.load_power": [{"mean": 200}] * 800,
            "sensor.battery_level": [{"mean": 50}] * 800,
        }
        assert extractor.has_sufficient_data(data) is True

    @pytest.mark.asyncio
    async def test_has_sufficient_data_false_missing(
        self, extractor: DataExtractor
    ) -> None:
        """Test sufficient data check fails with missing entity."""
        data = {
            "sensor.total_dc_power": [{"mean": 100}] * 800,
            # Missing load_power
            "sensor.battery_level": [{"mean": 50}] * 800,
        }
        assert extractor.has_sufficient_data(data) is False

    @pytest.mark.asyncio
    async def test_has_sufficient_data_false_insufficient(
        self, extractor: DataExtractor
    ) -> None:
        """Test sufficient data check fails with too few records."""
        data = {
            "sensor.total_dc_power": [{"mean": 100}] * 100,  # Only 100 records
            "sensor.load_power": [{"mean": 200}] * 100,
            "sensor.battery_level": [{"mean": 50}] * 100,
        }
        assert extractor.has_sufficient_data(data) is False

    def test_extract_recent_data_hours(self, extractor: DataExtractor) -> None:
        """Test extracting recent data with custom hours."""
        # Just verify the method exists and accepts hours parameter
        assert hasattr(extractor, "extract_recent_data")
```

**Step 6: Run all tests**

```bash
pytest tests/test_data_extractor.py -v
```
Expected: PASS

**Step 7: Commit**

```bash
git add custom_components/battery_energy_trading/ai/data_extractor.py tests/test_data_extractor.py
git commit -m "feat(ai): implement data extractor for HA statistics"
```

---

### Task 1.3: Implement Feature Engineering

**Files:**
- Create: `custom_components/battery_energy_trading/ai/feature_engineering.py`
- Create: `tests/test_feature_engineering.py`

**Step 1: Write failing test**

```python
"""Tests for feature engineering."""
import pytest
from datetime import datetime
import numpy as np

from custom_components.battery_energy_trading.ai.feature_engineering import (
    FeatureEngineering,
    create_time_features,
    create_lag_features,
)


class TestFeatureEngineering:
    """Test feature engineering."""

    def test_create_time_features(self) -> None:
        """Test time feature creation."""
        dt = datetime(2025, 6, 15, 14, 30)  # Sunday in June, 14:30
        features = create_time_features(dt)

        assert features["hour"] == 14
        assert features["day_of_week"] == 6  # Sunday
        assert features["month"] == 6
        assert features["is_weekend"] == 1
        assert features["day_of_year"] == 166

    def test_create_time_features_weekday(self) -> None:
        """Test time features on weekday."""
        dt = datetime(2025, 12, 2, 9, 0)  # Tuesday
        features = create_time_features(dt)

        assert features["is_weekend"] == 0
        assert features["day_of_week"] == 1  # Tuesday

    def test_create_lag_features(self) -> None:
        """Test lag feature creation."""
        values = list(range(200))  # 0, 1, 2, ..., 199
        lags = [1, 24, 168]  # 1 hour, 1 day, 1 week

        features = create_lag_features(values, lags, current_idx=199)

        assert features["lag_1"] == 198
        assert features["lag_24"] == 175
        assert features["lag_168"] == 31

    def test_create_lag_features_insufficient_data(self) -> None:
        """Test lag features with insufficient history."""
        values = [1, 2, 3, 4, 5]
        lags = [1, 24]  # 24 is more than available

        features = create_lag_features(values, lags, current_idx=4)

        assert features["lag_1"] == 4
        assert features["lag_24"] is None  # Not enough data
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_feature_engineering.py -v
```
Expected: FAIL (module not found)

**Step 3: Implement feature engineering**

```python
"""Feature engineering for AI models."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import numpy as np

_LOGGER = logging.getLogger(__name__)


def create_time_features(dt: datetime) -> dict[str, int | float]:
    """Create time-based features from datetime.

    Args:
        dt: Datetime to extract features from

    Returns:
        Dictionary of time features
    """
    return {
        "hour": dt.hour,
        "day_of_week": dt.weekday(),
        "day_of_year": dt.timetuple().tm_yday,
        "month": dt.month,
        "is_weekend": 1 if dt.weekday() >= 5 else 0,
        "hour_sin": np.sin(2 * np.pi * dt.hour / 24),
        "hour_cos": np.cos(2 * np.pi * dt.hour / 24),
        "month_sin": np.sin(2 * np.pi * dt.month / 12),
        "month_cos": np.cos(2 * np.pi * dt.month / 12),
    }


def create_lag_features(
    values: list[float],
    lags: list[int],
    current_idx: int,
) -> dict[str, float | None]:
    """Create lag features from time series.

    Args:
        values: List of historical values
        lags: List of lag periods (e.g., [1, 24, 168] for 1h, 1d, 1w)
        current_idx: Current position in values list

    Returns:
        Dictionary of lag features
    """
    features = {}
    for lag in lags:
        idx = current_idx - lag
        if idx >= 0 and idx < len(values):
            features[f"lag_{lag}"] = values[idx]
        else:
            features[f"lag_{lag}"] = None
    return features


def create_rolling_features(
    values: list[float],
    windows: list[int],
    current_idx: int,
) -> dict[str, float | None]:
    """Create rolling average features.

    Args:
        values: List of historical values
        windows: List of window sizes (e.g., [4, 24] for 4h, 24h averages)
        current_idx: Current position in values list

    Returns:
        Dictionary of rolling features
    """
    features = {}
    for window in windows:
        start_idx = max(0, current_idx - window + 1)
        if start_idx < current_idx:
            window_values = values[start_idx : current_idx + 1]
            features[f"rolling_mean_{window}"] = np.mean(window_values)
            features[f"rolling_std_{window}"] = np.std(window_values)
        else:
            features[f"rolling_mean_{window}"] = None
            features[f"rolling_std_{window}"] = None
    return features


class FeatureEngineering:
    """Feature engineering for AI training and inference."""

    def __init__(self) -> None:
        """Initialize feature engineering."""
        self.lags = [1, 24, 168]  # 1h, 1d, 1w
        self.windows = [4, 24, 168]  # 4h, 1d, 1w rolling averages

    def create_solar_features(
        self,
        timestamp: datetime,
        solar_history: list[float],
        forecast_solar: float,
        forecast_history: list[float],
        weather_data: dict[str, float],
        current_idx: int,
    ) -> dict[str, Any]:
        """Create features for solar prediction model.

        Args:
            timestamp: Current timestamp
            solar_history: Historical solar production values
            forecast_solar: Forecast.Solar prediction
            forecast_history: Historical forecast values
            weather_data: Weather features (cloud_cover, temperature)
            current_idx: Current index in history arrays

        Returns:
            Feature dictionary for solar model
        """
        features = {}

        # Time features
        features.update(create_time_features(timestamp))

        # Forecast.Solar as primary input
        features["forecast_solar"] = forecast_solar

        # Historical forecast error (actual - forecast)
        if len(solar_history) > 0 and len(forecast_history) > 0:
            min_len = min(len(solar_history), len(forecast_history))
            errors = [
                solar_history[i] - forecast_history[i]
                for i in range(min_len)
                if solar_history[i] is not None and forecast_history[i] is not None
            ]
            if errors:
                features["forecast_error_mean"] = np.mean(errors[-168:])  # Last week
                features["forecast_error_std"] = np.std(errors[-168:])
            else:
                features["forecast_error_mean"] = 0.0
                features["forecast_error_std"] = 0.0
        else:
            features["forecast_error_mean"] = 0.0
            features["forecast_error_std"] = 0.0

        # Weather features
        features["cloud_cover"] = weather_data.get("cloud_cover", 0)
        features["temperature"] = weather_data.get("temperature", 20)

        # Lag features from actual solar
        if solar_history:
            lag_features = create_lag_features(solar_history, self.lags, current_idx)
            features.update({f"solar_{k}": v for k, v in lag_features.items()})

        return features

    def create_load_features(
        self,
        timestamp: datetime,
        load_history: list[float],
        temperature: float,
        heat_pump_history: dict[str, list[int]],
        current_idx: int,
    ) -> dict[str, Any]:
        """Create features for load prediction model.

        Args:
            timestamp: Current timestamp
            load_history: Historical load values
            temperature: Current outdoor temperature
            heat_pump_history: Historical heat pump stage states
            current_idx: Current index in history arrays

        Returns:
            Feature dictionary for load model
        """
        features = {}

        # Time features
        features.update(create_time_features(timestamp))

        # Temperature (key predictor for heat pump)
        features["temperature"] = temperature
        features["temp_squared"] = temperature ** 2  # Non-linear relationship

        # Temperature bands for heat pump prediction
        features["temp_below_0"] = 1 if temperature < 0 else 0
        features["temp_below_5"] = 1 if temperature < 5 else 0
        features["temp_below_10"] = 1 if temperature < 10 else 0
        features["temp_below_15"] = 1 if temperature < 15 else 0

        # Historical load patterns
        if load_history:
            features.update(create_lag_features(load_history, self.lags, current_idx))
            features.update(
                create_rolling_features(load_history, self.windows, current_idx)
            )

        # Heat pump stage indicators
        for stage, history in heat_pump_history.items():
            if history and current_idx < len(history):
                features[f"hp_{stage}_active"] = history[current_idx]
            else:
                features[f"hp_{stage}_active"] = 0

        return features

    def create_decision_features(
        self,
        timestamp: datetime,
        battery_soc: float,
        current_price: float,
        prices_24h: list[float],
        solar_forecast: float,
        load_forecast: float,
    ) -> dict[str, Any]:
        """Create features for Q-learning decision model.

        Nord Pool prices are PRIMARY - included prominently.

        Args:
            timestamp: Current timestamp
            battery_soc: Battery state of charge (0-100)
            current_price: Current Nord Pool price
            prices_24h: Next 24 hours of prices
            solar_forecast: Predicted solar for next hour
            load_forecast: Predicted load for next hour

        Returns:
            Feature dictionary for decision model
        """
        features = {}

        # Time features
        features.update(create_time_features(timestamp))

        # Battery state (discretized)
        features["battery_soc"] = battery_soc
        features["battery_level"] = self._discretize_soc(battery_soc)

        # PRICES ARE PRIMARY
        features["current_price"] = current_price
        features["price_level"] = self._discretize_price(current_price, prices_24h)

        # Price statistics
        if prices_24h:
            features["price_mean_24h"] = np.mean(prices_24h)
            features["price_std_24h"] = np.std(prices_24h)
            features["price_min_24h"] = np.min(prices_24h)
            features["price_max_24h"] = np.max(prices_24h)
            features["price_percentile"] = self._price_percentile(
                current_price, prices_24h
            )

            # Price trend (next 6 hours vs current)
            if len(prices_24h) >= 6:
                features["price_trend_6h"] = np.mean(prices_24h[:6]) - current_price
            else:
                features["price_trend_6h"] = 0.0
        else:
            features["price_mean_24h"] = current_price
            features["price_std_24h"] = 0.0
            features["price_min_24h"] = current_price
            features["price_max_24h"] = current_price
            features["price_percentile"] = 50.0
            features["price_trend_6h"] = 0.0

        # Solar and load forecasts
        features["solar_forecast"] = solar_forecast
        features["load_forecast"] = load_forecast
        features["net_forecast"] = solar_forecast - load_forecast

        return features

    def _discretize_soc(self, soc: float) -> int:
        """Discretize battery SOC into 5 levels."""
        if soc < 20:
            return 0
        elif soc < 40:
            return 1
        elif soc < 60:
            return 2
        elif soc < 80:
            return 3
        else:
            return 4

    def _discretize_price(self, price: float, prices_24h: list[float]) -> int:
        """Discretize price into 5 levels based on distribution."""
        if not prices_24h:
            return 2  # Medium

        percentile = self._price_percentile(price, prices_24h)
        if percentile < 20:
            return 0  # Very low
        elif percentile < 40:
            return 1  # Low
        elif percentile < 60:
            return 2  # Medium
        elif percentile < 80:
            return 3  # High
        else:
            return 4  # Very high

    def _price_percentile(self, price: float, prices: list[float]) -> float:
        """Calculate percentile of price in distribution."""
        if not prices:
            return 50.0
        below = sum(1 for p in prices if p < price)
        return (below / len(prices)) * 100
```

**Step 4: Run tests**

```bash
pytest tests/test_feature_engineering.py -v
```
Expected: PASS

**Step 5: Add comprehensive tests**

Add to `tests/test_feature_engineering.py`:

```python
    @pytest.fixture
    def feature_eng(self) -> FeatureEngineering:
        """Create feature engineering instance."""
        return FeatureEngineering()

    def test_create_rolling_features(self) -> None:
        """Test rolling average features."""
        from custom_components.battery_energy_trading.ai.feature_engineering import (
            create_rolling_features,
        )

        values = [10.0] * 30  # Constant values
        features = create_rolling_features(values, [4, 24], current_idx=29)

        assert features["rolling_mean_4"] == 10.0
        assert features["rolling_std_4"] == 0.0
        assert features["rolling_mean_24"] == 10.0

    def test_create_load_features(self, feature_eng: FeatureEngineering) -> None:
        """Test load feature creation."""
        dt = datetime(2025, 1, 15, 18, 0)  # Winter evening
        load_history = [2000.0] * 200
        heat_pump_history = {
            "3kw": [0] * 200,
            "6kw": [1] * 200,  # 6kW stage active
        }

        features = feature_eng.create_load_features(
            timestamp=dt,
            load_history=load_history,
            temperature=-5.0,  # Cold
            heat_pump_history=heat_pump_history,
            current_idx=199,
        )

        assert features["temperature"] == -5.0
        assert features["temp_below_0"] == 1
        assert features["temp_below_5"] == 1
        assert features["hp_6kw_active"] == 1

    def test_create_decision_features_price_primary(
        self, feature_eng: FeatureEngineering
    ) -> None:
        """Test decision features with price as primary."""
        dt = datetime(2025, 12, 2, 17, 0)
        prices = [0.10, 0.15, 0.40, 0.35, 0.20] * 5  # 25 prices

        features = feature_eng.create_decision_features(
            timestamp=dt,
            battery_soc=60.0,
            current_price=0.40,  # High price
            prices_24h=prices[:24],
            solar_forecast=0.5,
            load_forecast=2.0,
        )

        assert features["current_price"] == 0.40
        assert features["price_level"] == 4  # Very high (top 20%)
        assert features["battery_level"] == 2  # 60% = level 2
        assert features["net_forecast"] == -1.5  # Solar - load
```

**Step 6: Run all tests**

```bash
pytest tests/test_feature_engineering.py -v
```
Expected: PASS

**Step 7: Update AI module init**

```python
"""AI module for smart battery management."""
from __future__ import annotations

from .config import AIConfig
from .data_extractor import DataExtractor
from .feature_engineering import (
    FeatureEngineering,
    create_lag_features,
    create_rolling_features,
    create_time_features,
)

__all__ = [
    "AIConfig",
    "DataExtractor",
    "FeatureEngineering",
    "create_lag_features",
    "create_rolling_features",
    "create_time_features",
]
```

**Step 8: Commit**

```bash
git add custom_components/battery_energy_trading/ai/feature_engineering.py \
        custom_components/battery_energy_trading/ai/__init__.py \
        tests/test_feature_engineering.py
git commit -m "feat(ai): implement feature engineering for ML models"
```

---

## Phase 2: Solar Predictor (Correction Layer)

### Task 2.1: Implement Base Model Interface

**Files:**
- Create: `custom_components/battery_energy_trading/ai/models/__init__.py`
- Create: `custom_components/battery_energy_trading/ai/models/base.py`
- Create: `tests/test_ai_models_base.py`

**Step 1: Write failing test**

```python
"""Tests for base model interface."""
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock

from custom_components.battery_energy_trading.ai.models.base import BaseModel


class TestBaseModel:
    """Test base model interface."""

    def test_cannot_instantiate_base(self) -> None:
        """Test that BaseModel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseModel()  # type: ignore

    def test_subclass_must_implement_methods(self) -> None:
        """Test that subclass must implement abstract methods."""

        class IncompleteModel(BaseModel):
            pass

        with pytest.raises(TypeError):
            IncompleteModel()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_ai_models_base.py -v
```
Expected: FAIL (module not found)

**Step 3: Implement base model**

```python
"""Base model interface for AI models."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

_LOGGER = logging.getLogger(__name__)


class BaseModel(ABC):
    """Abstract base class for AI models."""

    def __init__(self, name: str) -> None:
        """Initialize base model.

        Args:
            name: Model name for logging and file naming
        """
        self.name = name
        self._is_trained = False
        self._model: Any = None

    @property
    def is_trained(self) -> bool:
        """Check if model has been trained."""
        return self._is_trained

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        """Train the model.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target values (n_samples,)

        Returns:
            Training metrics (loss, accuracy, etc.)
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            Predictions (n_samples,)
        """
        pass

    @abstractmethod
    def save(self, path: Path) -> None:
        """Save model to disk.

        Args:
            path: Directory path to save model
        """
        pass

    @abstractmethod
    def load(self, path: Path) -> None:
        """Load model from disk.

        Args:
            path: Directory path containing saved model
        """
        pass

    def export_onnx(self, path: Path, input_shape: tuple[int, ...]) -> None:
        """Export model to ONNX format for inference.

        Args:
            path: Path for ONNX file
            input_shape: Shape of input features
        """
        raise NotImplementedError(f"{self.name} does not support ONNX export")

    def get_feature_importance(self) -> dict[str, float] | None:
        """Get feature importance if supported.

        Returns:
            Dictionary mapping feature names to importance scores, or None
        """
        return None
```

**Step 4: Create models init**

```python
"""AI models for battery energy trading."""
from __future__ import annotations

from .base import BaseModel

__all__ = ["BaseModel"]
```

**Step 5: Run tests**

```bash
pytest tests/test_ai_models_base.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add custom_components/battery_energy_trading/ai/models/ tests/test_ai_models_base.py
git commit -m "feat(ai): add base model interface"
```

---

### Task 2.2: Implement Solar Predictor Model

**Files:**
- Create: `custom_components/battery_energy_trading/ai/models/solar_predictor.py`
- Create: `tests/test_solar_predictor.py`

**Step 1: Write failing test**

```python
"""Tests for solar prediction model."""
import pytest
import numpy as np
from pathlib import Path
import tempfile

from custom_components.battery_energy_trading.ai.models.solar_predictor import (
    SolarPredictor,
)


class TestSolarPredictor:
    """Test solar predictor model."""

    @pytest.fixture
    def predictor(self) -> SolarPredictor:
        """Create solar predictor."""
        return SolarPredictor(n_estimators=10, max_depth=3)  # Small for tests

    @pytest.fixture
    def training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Create synthetic training data."""
        np.random.seed(42)
        n_samples = 500
        n_features = 10

        X = np.random.randn(n_samples, n_features)
        # Target is correction factor based on some features
        y = 0.9 + 0.2 * X[:, 0] + np.random.randn(n_samples) * 0.05
        y = np.clip(y, 0.5, 1.5)  # Correction factors between 0.5 and 1.5

        return X, y

    def test_init(self, predictor: SolarPredictor) -> None:
        """Test predictor initialization."""
        assert predictor.name == "solar_predictor"
        assert predictor.is_trained is False

    def test_train(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test model training."""
        X, y = training_data
        metrics = predictor.train(X, y)

        assert predictor.is_trained is True
        assert "mse" in metrics
        assert "mae" in metrics
        assert metrics["mse"] >= 0

    def test_predict_before_train(self, predictor: SolarPredictor) -> None:
        """Test prediction fails before training."""
        X = np.random.randn(10, 10)
        with pytest.raises(RuntimeError):
            predictor.predict(X)

    def test_predict_after_train(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test prediction after training."""
        X, y = training_data
        predictor.train(X, y)

        predictions = predictor.predict(X[:10])
        assert predictions.shape == (10,)
        assert np.all(predictions > 0)  # Correction factors should be positive

    def test_save_and_load(
        self, predictor: SolarPredictor, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test saving and loading model."""
        X, y = training_data
        predictor.train(X, y)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            predictor.save(path)

            new_predictor = SolarPredictor()
            new_predictor.load(path)

            assert new_predictor.is_trained is True
            # Predictions should match
            original_pred = predictor.predict(X[:5])
            loaded_pred = new_predictor.predict(X[:5])
            np.testing.assert_array_almost_equal(original_pred, loaded_pred)

    def test_correct_forecast(self, predictor: SolarPredictor) -> None:
        """Test applying correction to forecast."""
        # Test the high-level API
        assert hasattr(predictor, "correct_forecast")
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_solar_predictor.py -v
```
Expected: FAIL (module not found)

**Step 3: Implement solar predictor**

```python
"""Solar prediction model - correction layer for Forecast.Solar."""
from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score

from .base import BaseModel

_LOGGER = logging.getLogger(__name__)


class SolarPredictor(BaseModel):
    """Solar production predictor using Forecast.Solar correction.

    This model learns to correct Forecast.Solar predictions based on
    local patterns (shade, orientation, weather correlation).
    """

    def __init__(
        self,
        n_estimators: int = 50,
        max_depth: int = 5,
        learning_rate: float = 0.1,
    ) -> None:
        """Initialize solar predictor.

        Args:
            n_estimators: Number of boosting iterations
            max_depth: Maximum tree depth
            learning_rate: Boosting learning rate
        """
        super().__init__(name="solar_predictor")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self._model: GradientBoostingRegressor | None = None
        self._feature_names: list[str] = []

    def train(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        """Train the solar correction model.

        Args:
            X: Feature matrix
            y: Target correction factors (actual/forecast ratios)

        Returns:
            Training metrics
        """
        _LOGGER.info("Training solar predictor with %d samples", len(X))

        self._model = GradientBoostingRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=42,
        )

        # Cross-validation for metrics
        cv_scores = cross_val_score(
            self._model, X, y, cv=5, scoring="neg_mean_squared_error"
        )

        # Fit on full data
        self._model.fit(X, y)
        self._is_trained = True

        # Calculate metrics
        predictions = self._model.predict(X)
        mse = np.mean((predictions - y) ** 2)
        mae = np.mean(np.abs(predictions - y))

        metrics = {
            "mse": float(mse),
            "mae": float(mae),
            "cv_mse_mean": float(-cv_scores.mean()),
            "cv_mse_std": float(cv_scores.std()),
        }

        _LOGGER.info("Solar predictor trained: MSE=%.4f, MAE=%.4f", mse, mae)
        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict correction factors.

        Args:
            X: Feature matrix

        Returns:
            Correction factors (multiply Forecast.Solar by these)
        """
        if not self._is_trained or self._model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        predictions = self._model.predict(X)
        # Clip to reasonable range (0.5 to 1.5 correction)
        return np.clip(predictions, 0.5, 1.5)

    def correct_forecast(
        self, forecast_value: float, features: np.ndarray
    ) -> tuple[float, float]:
        """Apply correction to Forecast.Solar prediction.

        Args:
            forecast_value: Original Forecast.Solar prediction (kWh)
            features: Feature vector for this prediction

        Returns:
            Tuple of (corrected_value, correction_factor)
        """
        if not self._is_trained:
            # Return original if not trained
            return forecast_value, 1.0

        # Ensure 2D array
        if features.ndim == 1:
            features = features.reshape(1, -1)

        correction = self.predict(features)[0]
        corrected = forecast_value * correction

        return corrected, correction

    def save(self, path: Path) -> None:
        """Save model to disk.

        Args:
            path: Directory to save model
        """
        if not self._is_trained or self._model is None:
            raise RuntimeError("Cannot save untrained model")

        path.mkdir(parents=True, exist_ok=True)
        model_path = path / "solar_predictor.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(
                {
                    "model": self._model,
                    "n_estimators": self.n_estimators,
                    "max_depth": self.max_depth,
                    "learning_rate": self.learning_rate,
                    "feature_names": self._feature_names,
                },
                f,
            )

        _LOGGER.info("Saved solar predictor to %s", model_path)

    def load(self, path: Path) -> None:
        """Load model from disk.

        Args:
            path: Directory containing saved model
        """
        model_path = path / "solar_predictor.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")

        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self._model = data["model"]
        self.n_estimators = data["n_estimators"]
        self.max_depth = data["max_depth"]
        self.learning_rate = data["learning_rate"]
        self._feature_names = data.get("feature_names", [])
        self._is_trained = True

        _LOGGER.info("Loaded solar predictor from %s", model_path)

    def get_feature_importance(self) -> dict[str, float] | None:
        """Get feature importance scores.

        Returns:
            Dictionary of feature importances
        """
        if not self._is_trained or self._model is None:
            return None

        importances = self._model.feature_importances_
        if self._feature_names:
            return dict(zip(self._feature_names, importances))
        return {f"feature_{i}": imp for i, imp in enumerate(importances)}

    def set_feature_names(self, names: list[str]) -> None:
        """Set feature names for importance reporting.

        Args:
            names: List of feature names
        """
        self._feature_names = names
```

**Step 4: Run tests**

```bash
pytest tests/test_solar_predictor.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/battery_energy_trading/ai/models/solar_predictor.py \
        tests/test_solar_predictor.py
git commit -m "feat(ai): implement solar predictor correction model"
```

---

## Phase 3: Load Forecaster

### Task 3.1: Implement Load Forecaster Model

**Files:**
- Create: `custom_components/battery_energy_trading/ai/models/load_forecaster.py`
- Create: `tests/test_load_forecaster.py`

**Step 1: Write failing test**

```python
"""Tests for load forecasting model."""
import pytest
import numpy as np
from pathlib import Path
import tempfile

from custom_components.battery_energy_trading.ai.models.load_forecaster import (
    LoadForecaster,
)


class TestLoadForecaster:
    """Test load forecaster model."""

    @pytest.fixture
    def forecaster(self) -> LoadForecaster:
        """Create load forecaster."""
        return LoadForecaster(n_estimators=10)  # Small for tests

    @pytest.fixture
    def training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Create synthetic training data."""
        np.random.seed(42)
        n_samples = 500
        n_features = 15

        X = np.random.randn(n_samples, n_features)
        # Target is load based on temperature and time
        y = 2000 + 500 * X[:, 0] + np.random.randn(n_samples) * 100
        y = np.clip(y, 500, 10000)

        return X, y

    def test_init(self, forecaster: LoadForecaster) -> None:
        """Test forecaster initialization."""
        assert forecaster.name == "load_forecaster"
        assert forecaster.is_trained is False

    def test_train(
        self, forecaster: LoadForecaster, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test model training."""
        X, y = training_data
        metrics = forecaster.train(X, y)

        assert forecaster.is_trained is True
        assert "mse" in metrics
        assert "mape" in metrics

    def test_predict_load(
        self, forecaster: LoadForecaster, training_data: tuple[np.ndarray, np.ndarray]
    ) -> None:
        """Test load prediction."""
        X, y = training_data
        forecaster.train(X, y)

        predictions = forecaster.predict(X[:10])
        assert predictions.shape == (10,)
        assert np.all(predictions > 0)  # Load should be positive

    def test_predict_heat_pump_stage(self, forecaster: LoadForecaster) -> None:
        """Test heat pump stage prediction."""
        assert hasattr(forecaster, "predict_heat_pump_stage")

        # Test temperature to stage mapping
        stage = forecaster.predict_heat_pump_stage(-10.0)  # Very cold
        assert stage in [12, 15]  # Should be high stage

        stage = forecaster.predict_heat_pump_stage(20.0)  # Warm
        assert stage == 0  # Heat pump off
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_load_forecaster.py -v
```
Expected: FAIL (module not found)

**Step 3: Implement load forecaster**

```python
"""Load forecasting model with heat pump awareness."""
from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score

from .base import BaseModel

_LOGGER = logging.getLogger(__name__)


class LoadForecaster(BaseModel):
    """Load forecaster with heat pump stage modeling.

    Uses ensemble of models for robust predictions.
    Heat pump is modeled separately with temperature-based stages.
    """

    # Heat pump power stages (kW) by temperature threshold
    HEAT_PUMP_STAGES = {
        15: 0,    # Above 15°C: off
        10: 3,    # 10-15°C: 3kW
        5: 6,     # 5-10°C: 6kW
        0: 9,     # 0-5°C: 9kW
        -5: 12,   # -5-0°C: 12kW
        -999: 15,  # Below -5°C: 15kW
    }

    def __init__(
        self,
        n_estimators: int = 50,
        use_ensemble: bool = True,
    ) -> None:
        """Initialize load forecaster.

        Args:
            n_estimators: Number of estimators for tree models
            use_ensemble: Whether to use ensemble of models
        """
        super().__init__(name="load_forecaster")
        self.n_estimators = n_estimators
        self.use_ensemble = use_ensemble
        self._models: list[tuple[str, object]] = []
        self._feature_names: list[str] = []

    def train(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        """Train the load forecaster ensemble.

        Args:
            X: Feature matrix
            y: Target load values (watts)

        Returns:
            Training metrics
        """
        _LOGGER.info("Training load forecaster with %d samples", len(X))

        self._models = []

        if self.use_ensemble:
            # Gradient Boosting
            gb = GradientBoostingRegressor(
                n_estimators=self.n_estimators,
                max_depth=5,
                random_state=42,
            )
            gb.fit(X, y)
            self._models.append(("gradient_boosting", gb))

            # Random Forest
            rf = RandomForestRegressor(
                n_estimators=self.n_estimators,
                max_depth=8,
                random_state=42,
            )
            rf.fit(X, y)
            self._models.append(("random_forest", rf))

            # Ridge Regression (for stability)
            ridge = Ridge(alpha=1.0)
            ridge.fit(X, y)
            self._models.append(("ridge", ridge))
        else:
            # Single model
            gb = GradientBoostingRegressor(
                n_estimators=self.n_estimators,
                max_depth=5,
                random_state=42,
            )
            gb.fit(X, y)
            self._models.append(("gradient_boosting", gb))

        self._is_trained = True

        # Calculate metrics
        predictions = self.predict(X)
        mse = np.mean((predictions - y) ** 2)
        mae = np.mean(np.abs(predictions - y))
        mape = np.mean(np.abs((predictions - y) / np.maximum(y, 1))) * 100

        metrics = {
            "mse": float(mse),
            "mae": float(mae),
            "mape": float(mape),
            "n_models": len(self._models),
        }

        _LOGGER.info("Load forecaster trained: MAE=%.1f W, MAPE=%.1f%%", mae, mape)
        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict load values.

        Args:
            X: Feature matrix

        Returns:
            Predicted load values (watts)
        """
        if not self._is_trained or not self._models:
            raise RuntimeError("Model not trained. Call train() first.")

        # Ensemble prediction (average of all models)
        predictions = []
        for name, model in self._models:
            pred = model.predict(X)
            predictions.append(pred)

        ensemble_pred = np.mean(predictions, axis=0)
        # Ensure non-negative load
        return np.maximum(ensemble_pred, 0)

    def predict_heat_pump_stage(self, temperature: float) -> int:
        """Predict heat pump power stage based on temperature.

        Args:
            temperature: Outdoor temperature in Celsius

        Returns:
            Predicted power stage in kW (0, 3, 6, 9, 12, or 15)
        """
        for threshold, stage in sorted(
            self.HEAT_PUMP_STAGES.items(), reverse=True
        ):
            if temperature > threshold:
                return stage
        return 15  # Coldest default

    def predict_with_heat_pump(
        self,
        X: np.ndarray,
        temperatures: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Predict load with explicit heat pump component.

        Args:
            X: Feature matrix
            temperatures: Outdoor temperatures

        Returns:
            Tuple of (total_load, heat_pump_load)
        """
        base_load = self.predict(X)
        hp_load = np.array([
            self.predict_heat_pump_stage(t) * 1000
            for t in temperatures
        ])

        return base_load, hp_load

    def save(self, path: Path) -> None:
        """Save model to disk."""
        if not self._is_trained:
            raise RuntimeError("Cannot save untrained model")

        path.mkdir(parents=True, exist_ok=True)
        model_path = path / "load_forecaster.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(
                {
                    "models": self._models,
                    "n_estimators": self.n_estimators,
                    "use_ensemble": self.use_ensemble,
                    "feature_names": self._feature_names,
                },
                f,
            )

        _LOGGER.info("Saved load forecaster to %s", model_path)

    def load(self, path: Path) -> None:
        """Load model from disk."""
        model_path = path / "load_forecaster.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")

        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self._models = data["models"]
        self.n_estimators = data["n_estimators"]
        self.use_ensemble = data["use_ensemble"]
        self._feature_names = data.get("feature_names", [])
        self._is_trained = True

        _LOGGER.info("Loaded load forecaster from %s", model_path)

    def set_feature_names(self, names: list[str]) -> None:
        """Set feature names for reporting."""
        self._feature_names = names
```

**Step 4: Run tests**

```bash
pytest tests/test_load_forecaster.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/battery_energy_trading/ai/models/load_forecaster.py \
        tests/test_load_forecaster.py
git commit -m "feat(ai): implement load forecaster with heat pump modeling"
```

---

## Phase 4: Decision Optimizer (Q-Learning)

### Task 4.1: Implement Q-Learning Agent

**Files:**
- Create: `custom_components/battery_energy_trading/ai/models/decision_optimizer.py`
- Create: `tests/test_decision_optimizer.py`

**Step 1: Write failing test**

```python
"""Tests for Q-learning decision optimizer."""
import pytest
import numpy as np

from custom_components.battery_energy_trading.ai.models.decision_optimizer import (
    DecisionOptimizer,
    Action,
)


class TestDecisionOptimizer:
    """Test Q-learning decision optimizer."""

    @pytest.fixture
    def optimizer(self) -> DecisionOptimizer:
        """Create decision optimizer."""
        return DecisionOptimizer(
            learning_rate=0.1,
            discount_factor=0.9,
            exploration_rate=0.1,
        )

    def test_init(self, optimizer: DecisionOptimizer) -> None:
        """Test optimizer initialization."""
        assert optimizer.name == "decision_optimizer"
        assert len(optimizer.q_table) == 0

    def test_actions(self) -> None:
        """Test action enum."""
        assert Action.CHARGE_HIGH.value == 0
        assert Action.HOLD.value == 2
        assert Action.DISCHARGE_HIGH.value == 4

    def test_get_action_training_mode(self, optimizer: DecisionOptimizer) -> None:
        """Test action selection in training mode."""
        state = (2, 3, 1)  # Example state tuple
        action = optimizer.get_action(state, training=True)
        assert isinstance(action, Action)

    def test_get_action_inference_mode(self, optimizer: DecisionOptimizer) -> None:
        """Test action selection in inference mode."""
        state = (2, 3, 1)
        # Set a Q value
        optimizer.q_table[state] = {Action.DISCHARGE_HIGH: 10.0}
        action = optimizer.get_action(state, training=False)
        assert action == Action.DISCHARGE_HIGH

    def test_update_q_value(self, optimizer: DecisionOptimizer) -> None:
        """Test Q-value update."""
        state = (2, 3, 1)
        action = Action.DISCHARGE_HIGH
        next_state = (1, 2, 1)
        reward = 5.0

        initial_q = optimizer.get_q_value(state, action)
        optimizer.update(state, action, reward, next_state)
        updated_q = optimizer.get_q_value(state, action)

        assert updated_q != initial_q

    def test_price_primary_in_reward(self, optimizer: DecisionOptimizer) -> None:
        """Test that price is primary factor in reward calculation."""
        # High price discharge should be rewarded
        reward_high = optimizer.calculate_reward(
            action=Action.DISCHARGE_HIGH,
            price=0.40,
            energy_kwh=5.0,
            battery_change=-5.0,
        )

        # Low price discharge should be penalized
        reward_low = optimizer.calculate_reward(
            action=Action.DISCHARGE_HIGH,
            price=0.05,
            energy_kwh=5.0,
            battery_change=-5.0,
        )

        assert reward_high > reward_low  # Price matters!
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_decision_optimizer.py -v
```
Expected: FAIL (module not found)

**Step 3: Implement Q-learning optimizer**

```python
"""Q-learning decision optimizer for battery control."""
from __future__ import annotations

import logging
import pickle
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from .base import BaseModel

_LOGGER = logging.getLogger(__name__)


class Action(Enum):
    """Battery control actions."""

    CHARGE_HIGH = 0    # Charge at max rate
    CHARGE_LOW = 1     # Charge at half rate
    HOLD = 2           # Self-consumption mode
    DISCHARGE_LOW = 3  # Discharge at half rate
    DISCHARGE_HIGH = 4 # Discharge at max rate


class DecisionOptimizer(BaseModel):
    """Q-learning agent for optimal charge/discharge decisions.

    CRITICAL: Nord Pool prices are the PRIMARY decision driver.
    This agent learns to optimize timing within price-selected windows.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        exploration_rate: float = 0.1,
    ) -> None:
        """Initialize Q-learning optimizer.

        Args:
            learning_rate: Alpha - how much new info overrides old
            discount_factor: Gamma - importance of future rewards
            exploration_rate: Epsilon - probability of random action
        """
        super().__init__(name="decision_optimizer")
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate

        # Q-table: state -> {action -> q_value}
        self.q_table: dict[tuple, dict[Action, float]] = {}

    def get_q_value(self, state: tuple, action: Action) -> float:
        """Get Q-value for state-action pair.

        Args:
            state: State tuple
            action: Action

        Returns:
            Q-value (0.0 if not seen before)
        """
        if state not in self.q_table:
            return 0.0
        return self.q_table[state].get(action, 0.0)

    def get_action(self, state: tuple, training: bool = False) -> Action:
        """Select action using epsilon-greedy policy.

        Args:
            state: Current state tuple
            training: Whether in training mode (exploration enabled)

        Returns:
            Selected action
        """
        # Exploration in training mode
        if training and np.random.random() < self.exploration_rate:
            return np.random.choice(list(Action))

        # Exploitation: select best action
        if state not in self.q_table:
            return Action.HOLD  # Default to safe action

        q_values = self.q_table[state]
        if not q_values:
            return Action.HOLD

        best_action = max(q_values.keys(), key=lambda a: q_values[a])
        return best_action

    def update(
        self,
        state: tuple,
        action: Action,
        reward: float,
        next_state: tuple,
    ) -> None:
        """Update Q-value using Q-learning update rule.

        Q(s,a) = Q(s,a) + α * (r + γ * max(Q(s',a')) - Q(s,a))

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Resulting state
        """
        # Initialize state if needed
        if state not in self.q_table:
            self.q_table[state] = {}

        # Current Q value
        current_q = self.get_q_value(state, action)

        # Max Q value for next state
        if next_state in self.q_table and self.q_table[next_state]:
            max_next_q = max(self.q_table[next_state].values())
        else:
            max_next_q = 0.0

        # Q-learning update
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )

        self.q_table[state][action] = new_q

    def calculate_reward(
        self,
        action: Action,
        price: float,
        energy_kwh: float,
        battery_change: float,
        solar_available: float = 0.0,
    ) -> float:
        """Calculate reward for action taken.

        PRICE IS PRIMARY FACTOR.

        Args:
            action: Action taken
            price: Current electricity price (EUR/kWh)
            energy_kwh: Energy transferred (positive = to grid)
            battery_change: Change in battery level
            solar_available: Solar power available

        Returns:
            Reward value
        """
        reward = 0.0

        # PRIMARY: Price-based revenue/cost
        if action in [Action.DISCHARGE_HIGH, Action.DISCHARGE_LOW]:
            # Revenue from selling at current price
            revenue = energy_kwh * price
            reward += revenue * 10  # Scale up price importance

            # Penalty for discharging at low prices
            if price < 0.10:
                reward -= 2.0

        elif action in [Action.CHARGE_HIGH, Action.CHARGE_LOW]:
            # Cost of buying at current price
            cost = energy_kwh * price
            reward -= cost * 10  # Scale up price importance

            # Bonus for charging at low prices
            if price < 0.05:
                reward += 2.0

        # Secondary: Battery cycle penalty
        cycle_penalty = abs(battery_change) * 0.01
        reward -= cycle_penalty

        # Secondary: Solar utilization bonus
        if action == Action.HOLD and solar_available > 0:
            reward += solar_available * 0.001  # Small bonus

        return reward

    def train(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        """Train from historical data.

        For Q-learning, training is done through experience replay.

        Args:
            X: State features (unused, states come from experience)
            y: Actions/rewards (unused, come from experience)

        Returns:
            Training metrics
        """
        # Q-learning trains through update() calls, not batch training
        self._is_trained = True
        return {"q_table_size": len(self.q_table)}

    def train_from_experience(
        self,
        experiences: list[tuple[tuple, Action, float, tuple]],
    ) -> dict[str, float]:
        """Train from list of experiences.

        Args:
            experiences: List of (state, action, reward, next_state) tuples

        Returns:
            Training metrics
        """
        _LOGGER.info("Training from %d experiences", len(experiences))

        for state, action, reward, next_state in experiences:
            self.update(state, action, reward, next_state)

        self._is_trained = True

        return {
            "experiences_processed": len(experiences),
            "q_table_size": len(self.q_table),
            "unique_states": len(self.q_table),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict best actions for states.

        Args:
            X: State features (converted to tuples internally)

        Returns:
            Action indices
        """
        actions = []
        for row in X:
            state = tuple(row.astype(int))
            action = self.get_action(state, training=False)
            actions.append(action.value)
        return np.array(actions)

    def get_recommendation(
        self,
        battery_level: int,
        price_level: int,
        solar_level: int,
        load_level: int,
        hour_period: int,
    ) -> tuple[Action, float]:
        """Get action recommendation with confidence.

        Args:
            battery_level: Discretized SOC (0-4)
            price_level: Discretized price (0-4)
            solar_level: Discretized solar (0-3)
            load_level: Discretized load (0-2)
            hour_period: Time period (0-5)

        Returns:
            Tuple of (recommended_action, confidence)
        """
        state = (battery_level, price_level, solar_level, load_level, hour_period)

        # Get action
        action = self.get_action(state, training=False)

        # Calculate confidence based on Q-value spread
        if state in self.q_table and len(self.q_table[state]) > 1:
            q_values = list(self.q_table[state].values())
            q_range = max(q_values) - min(q_values)
            confidence = min(q_range / 10.0, 1.0)  # Normalize to 0-1
        else:
            confidence = 0.5  # Default medium confidence

        return action, confidence

    def save(self, path: Path) -> None:
        """Save Q-table to disk."""
        path.mkdir(parents=True, exist_ok=True)
        model_path = path / "decision_optimizer.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(
                {
                    "q_table": self.q_table,
                    "learning_rate": self.learning_rate,
                    "discount_factor": self.discount_factor,
                    "exploration_rate": self.exploration_rate,
                },
                f,
            )

        _LOGGER.info("Saved decision optimizer to %s", model_path)

    def load(self, path: Path) -> None:
        """Load Q-table from disk."""
        model_path = path / "decision_optimizer.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")

        with open(model_path, "rb") as f:
            data = pickle.load(f)

        self.q_table = data["q_table"]
        self.learning_rate = data["learning_rate"]
        self.discount_factor = data["discount_factor"]
        self.exploration_rate = data["exploration_rate"]
        self._is_trained = True

        _LOGGER.info("Loaded decision optimizer from %s", model_path)
```

**Step 4: Run tests**

```bash
pytest tests/test_decision_optimizer.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/battery_energy_trading/ai/models/decision_optimizer.py \
        tests/test_decision_optimizer.py
git commit -m "feat(ai): implement Q-learning decision optimizer"
```

---

## Phase 5: Training Pipeline & Scheduler

### Task 5.1: Implement Training Orchestrator

**Files:**
- Create: `custom_components/battery_energy_trading/ai/training/__init__.py`
- Create: `custom_components/battery_energy_trading/ai/training/trainer.py`
- Create: `tests/test_trainer.py`

**Step 1: Write failing test**

```python
"""Tests for training orchestrator."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile

from custom_components.battery_energy_trading.ai.training.trainer import AITrainer
from custom_components.battery_energy_trading.ai.config import AIConfig


class TestAITrainer:
    """Test AI training orchestrator."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant."""
        hass = MagicMock()
        hass.config.path = MagicMock(return_value="/tmp/hass")
        return hass

    @pytest.fixture
    def config(self) -> AIConfig:
        """Create test config."""
        return AIConfig()

    @pytest.fixture
    def trainer(self, mock_hass: MagicMock, config: AIConfig) -> AITrainer:
        """Create trainer instance."""
        return AITrainer(mock_hass, config)

    def test_init(self, trainer: AITrainer) -> None:
        """Test trainer initialization."""
        assert trainer.hass is not None
        assert trainer.config is not None
        assert trainer.is_training is False

    @pytest.mark.asyncio
    async def test_train_all_models_insufficient_data(
        self, trainer: AITrainer
    ) -> None:
        """Test training fails with insufficient data."""
        with patch.object(
            trainer.data_extractor,
            "extract_training_data",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await trainer.train_all_models()
            assert result["success"] is False
            assert "insufficient" in result["error"].lower()

    def test_get_model_path(self, trainer: AITrainer) -> None:
        """Test model path generation."""
        path = trainer.get_model_path()
        assert "battery_energy_trading" in str(path)
        assert "models" in str(path)
```

**Step 2: Implement trainer**

```python
"""Training orchestrator for AI models."""
from __future__ import annotations

import asyncio
import gc
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from ..config import AIConfig
from ..data_extractor import DataExtractor
from ..feature_engineering import FeatureEngineering
from ..models.decision_optimizer import DecisionOptimizer
from ..models.load_forecaster import LoadForecaster
from ..models.solar_predictor import SolarPredictor

_LOGGER = logging.getLogger(__name__)


class AITrainer:
    """Orchestrates training of all AI models."""

    def __init__(self, hass: HomeAssistant, config: AIConfig) -> None:
        """Initialize trainer.

        Args:
            hass: Home Assistant instance
            config: AI configuration
        """
        self.hass = hass
        self.config = config
        self.data_extractor = DataExtractor(hass, config)
        self.feature_eng = FeatureEngineering()

        # Models
        self.solar_predictor: SolarPredictor | None = None
        self.load_forecaster: LoadForecaster | None = None
        self.decision_optimizer: DecisionOptimizer | None = None

        self._is_training = False
        self._last_training: datetime | None = None
        self._training_metrics: dict[str, Any] = {}

    @property
    def is_training(self) -> bool:
        """Check if training is in progress."""
        return self._is_training

    def get_model_path(self) -> Path:
        """Get path for model storage."""
        return Path(self.hass.config.path("custom_components/battery_energy_trading/models"))

    async def train_all_models(self) -> dict[str, Any]:
        """Train all AI models sequentially.

        Returns:
            Training result with metrics
        """
        if self._is_training:
            return {"success": False, "error": "Training already in progress"}

        self._is_training = True
        start_time = datetime.now()
        results: dict[str, Any] = {"success": True, "models": {}}

        try:
            _LOGGER.info("Starting AI model training")

            # Step 1: Extract data
            _LOGGER.info("Extracting training data...")
            data = await self.data_extractor.extract_training_data()

            if not self.data_extractor.has_sufficient_data(data):
                return {
                    "success": False,
                    "error": "Insufficient historical data for training",
                }

            # Step 2: Train solar predictor
            _LOGGER.info("Training solar predictor...")
            solar_result = await self._train_solar_model(data)
            results["models"]["solar"] = solar_result
            gc.collect()  # Free memory

            # Step 3: Train load forecaster
            _LOGGER.info("Training load forecaster...")
            load_result = await self._train_load_model(data)
            results["models"]["load"] = load_result
            gc.collect()

            # Step 4: Update Q-learning agent
            _LOGGER.info("Updating decision optimizer...")
            decision_result = await self._train_decision_model(data)
            results["models"]["decision"] = decision_result
            gc.collect()

            # Step 5: Save models
            await self._save_models()

            self._last_training = datetime.now()
            results["duration_seconds"] = (
                datetime.now() - start_time
            ).total_seconds()

            _LOGGER.info(
                "Training completed in %.1f seconds",
                results["duration_seconds"],
            )

        except Exception as err:
            _LOGGER.exception("Training failed: %s", err)
            results["success"] = False
            results["error"] = str(err)

        finally:
            self._is_training = False

        return results

    async def _train_solar_model(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> dict[str, Any]:
        """Train solar predictor model."""
        # Prepare features and targets
        # (Implementation details depend on data structure)
        X, y = self._prepare_solar_data(data)

        if len(X) < 100:
            return {"trained": False, "error": "Not enough solar data"}

        self.solar_predictor = SolarPredictor(
            n_estimators=self.config.solar_model_estimators,
            max_depth=self.config.solar_model_max_depth,
        )

        # Run training in executor to avoid blocking
        metrics = await self.hass.async_add_executor_job(
            self.solar_predictor.train, X, y
        )

        return {"trained": True, "metrics": metrics}

    async def _train_load_model(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> dict[str, Any]:
        """Train load forecaster model."""
        X, y = self._prepare_load_data(data)

        if len(X) < 100:
            return {"trained": False, "error": "Not enough load data"}

        self.load_forecaster = LoadForecaster(
            n_estimators=self.config.load_model_estimators,
        )

        metrics = await self.hass.async_add_executor_job(
            self.load_forecaster.train, X, y
        )

        return {"trained": True, "metrics": metrics}

    async def _train_decision_model(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> dict[str, Any]:
        """Train/update Q-learning decision optimizer."""
        experiences = self._prepare_decision_experiences(data)

        if len(experiences) < 50:
            return {"trained": False, "error": "Not enough decision data"}

        if self.decision_optimizer is None:
            self.decision_optimizer = DecisionOptimizer(
                learning_rate=self.config.q_learning_rate,
                discount_factor=self.config.q_discount_factor,
                exploration_rate=self.config.q_exploration_rate,
            )

        metrics = self.decision_optimizer.train_from_experience(experiences)
        return {"trained": True, "metrics": metrics}

    def _prepare_solar_data(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare solar training data.

        Returns:
            Tuple of (features, targets)
        """
        # Extract actual solar and forecast values
        solar_key = self.config.solar_power_entity
        forecast_key = self.config.solar_forecast_entity

        if solar_key not in data or forecast_key not in data:
            return np.array([]), np.array([])

        solar_data = data[solar_key]
        forecast_data = data[forecast_key]

        # Align timestamps and create features
        features = []
        targets = []

        # Simplified: create features from each data point
        for i, record in enumerate(solar_data):
            if i >= len(forecast_data):
                break

            actual = record.get("mean", 0) or 0
            forecast = forecast_data[i].get("mean", 0) or 0

            if forecast > 0:
                # Target is correction factor
                correction = actual / forecast
                correction = np.clip(correction, 0.5, 1.5)

                # Simple features for now
                dt = datetime.fromisoformat(record["start"])
                time_features = self.feature_eng.create_time_features(dt)
                feature_vec = [
                    forecast,
                    time_features["hour"],
                    time_features["month"],
                    time_features["is_weekend"],
                ]
                features.append(feature_vec)
                targets.append(correction)

        return np.array(features), np.array(targets)

    def _prepare_load_data(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare load training data."""
        load_key = self.config.load_power_entity
        temp_key = self.config.outdoor_temp_entity

        if load_key not in data:
            return np.array([]), np.array([])

        load_data = data[load_key]
        temp_data = data.get(temp_key, [])

        features = []
        targets = []

        for i, record in enumerate(load_data):
            load = record.get("mean", 0) or 0
            temp = temp_data[i].get("mean", 15) if i < len(temp_data) else 15

            dt = datetime.fromisoformat(record["start"])
            time_features = self.feature_eng.create_time_features(dt)

            feature_vec = [
                time_features["hour"],
                time_features["day_of_week"],
                time_features["month"],
                time_features["is_weekend"],
                temp,
            ]
            features.append(feature_vec)
            targets.append(load)

        return np.array(features), np.array(targets)

    def _prepare_decision_experiences(
        self, data: dict[str, list[dict[str, Any]]]
    ) -> list[tuple]:
        """Prepare experiences for Q-learning from historical data."""
        # This would reconstruct state-action-reward sequences
        # from historical battery/price data
        # Simplified placeholder
        return []

    async def _save_models(self) -> None:
        """Save trained models to disk."""
        model_path = self.get_model_path()
        model_path.mkdir(parents=True, exist_ok=True)

        if self.solar_predictor and self.solar_predictor.is_trained:
            await self.hass.async_add_executor_job(
                self.solar_predictor.save, model_path
            )

        if self.load_forecaster and self.load_forecaster.is_trained:
            await self.hass.async_add_executor_job(
                self.load_forecaster.save, model_path
            )

        if self.decision_optimizer and self.decision_optimizer.is_trained:
            await self.hass.async_add_executor_job(
                self.decision_optimizer.save, model_path
            )

    async def load_models(self) -> bool:
        """Load previously trained models.

        Returns:
            True if models loaded successfully
        """
        model_path = self.get_model_path()

        if not model_path.exists():
            _LOGGER.info("No saved models found")
            return False

        try:
            # Load solar predictor
            self.solar_predictor = SolarPredictor()
            await self.hass.async_add_executor_job(
                self.solar_predictor.load, model_path
            )

            # Load load forecaster
            self.load_forecaster = LoadForecaster()
            await self.hass.async_add_executor_job(
                self.load_forecaster.load, model_path
            )

            # Load decision optimizer
            self.decision_optimizer = DecisionOptimizer()
            await self.hass.async_add_executor_job(
                self.decision_optimizer.load, model_path
            )

            _LOGGER.info("Loaded AI models from %s", model_path)
            return True

        except Exception as err:
            _LOGGER.warning("Failed to load some models: %s", err)
            return False
```

**Step 3: Create training init**

```python
"""AI training module."""
from __future__ import annotations

from .trainer import AITrainer

__all__ = ["AITrainer"]
```

**Step 4: Run tests**

```bash
pytest tests/test_trainer.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add custom_components/battery_energy_trading/ai/training/ tests/test_trainer.py
git commit -m "feat(ai): implement training orchestrator"
```

---

## Phase 6: Integration & Services

### Task 6.1: Add AI Services

**Files:**
- Modify: `custom_components/battery_energy_trading/__init__.py`
- Modify: `custom_components/battery_energy_trading/services.yaml`

**Step 1: Add AI services to services.yaml**

Add to existing `services.yaml`:

```yaml
train_ai_models:
  name: Train AI Models
  description: Manually trigger AI model training
  fields:
    days_of_data:
      name: Days of Data
      description: Days of historical data to use (default 90)
      default: 90
      selector:
        number:
          min: 30
          max: 365

get_ai_prediction:
  name: Get AI Prediction
  description: Get current AI recommendation with explanation

set_ai_mode:
  name: Set AI Mode
  description: Enable or disable AI-driven decisions
  fields:
    enabled:
      name: Enabled
      description: Enable AI mode
      required: true
      selector:
        boolean:
```

**Step 2: Register services in __init__.py**

Add service handlers (integrate into existing `async_setup`):

```python
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Battery Energy Trading integration."""
    # ... existing code ...

    # AI Services
    async def handle_train_ai_models(call: ServiceCall) -> None:
        """Handle train AI models service."""
        entry_data = next(iter(hass.data.get(DOMAIN, {}).values()), None)
        if not entry_data or "ai_trainer" not in entry_data:
            raise HomeAssistantError("AI trainer not available")

        trainer = entry_data["ai_trainer"]
        days = call.data.get("days_of_data", 90)

        result = await trainer.train_all_models()

        hass.bus.async_fire(
            f"{DOMAIN}_ai_training_complete",
            {"success": result["success"], "metrics": result.get("models", {})},
        )

    async def handle_get_ai_prediction(call: ServiceCall) -> ServiceResponse:
        """Handle get AI prediction service."""
        entry_data = next(iter(hass.data.get(DOMAIN, {}).values()), None)
        if not entry_data or "ai_trainer" not in entry_data:
            raise HomeAssistantError("AI trainer not available")

        # Get current recommendation
        trainer = entry_data["ai_trainer"]
        if not trainer.decision_optimizer:
            return {"recommendation": "HOLD", "confidence": 0, "reason": "AI not trained"}

        # Would need current state from coordinator
        return {"recommendation": "HOLD", "confidence": 0.5, "reason": "Default"}

    async def handle_set_ai_mode(call: ServiceCall) -> None:
        """Handle set AI mode service."""
        enabled = call.data.get("enabled", False)

        for entry_data in hass.data.get(DOMAIN, {}).values():
            entry_data["ai_enabled"] = enabled

        hass.bus.async_fire(f"{DOMAIN}_ai_mode_changed", {"enabled": enabled})

    hass.services.async_register(DOMAIN, "train_ai_models", handle_train_ai_models)
    hass.services.async_register(
        DOMAIN,
        "get_ai_prediction",
        handle_get_ai_prediction,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, "set_ai_mode", handle_set_ai_mode)

    return True
```

**Step 3: Commit**

```bash
git add custom_components/battery_energy_trading/__init__.py \
        custom_components/battery_energy_trading/services.yaml
git commit -m "feat(ai): add AI service definitions and handlers"
```

---

### Task 6.2: Add AI Status Sensor

**Files:**
- Modify: `custom_components/battery_energy_trading/sensor.py`

**Step 1: Add AI status sensor class**

```python
class AIStatusSensor(BatteryEnergyTradingBaseEntity, SensorEntity):
    """Sensor for AI system status."""

    _attr_icon = "mdi:robot"

    def __init__(
        self,
        coordinator: BatteryEnergyTradingCoordinator,
        config_entry: ConfigEntry,
        ai_trainer: AITrainer | None,
    ) -> None:
        """Initialize AI status sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._ai_trainer = ai_trainer
        self._attr_unique_id = f"{config_entry.entry_id}_ai_status"
        self._attr_name = "AI Status"

    @property
    def native_value(self) -> str:
        """Return AI status."""
        if self._ai_trainer is None:
            return "Not Configured"
        if self._ai_trainer.is_training:
            return "Training"
        if self._ai_trainer.decision_optimizer and self._ai_trainer.decision_optimizer.is_trained:
            return "Ready"
        return "Initializing"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return AI status attributes."""
        attrs = {}
        if self._ai_trainer:
            attrs["last_training"] = (
                self._ai_trainer._last_training.isoformat()
                if self._ai_trainer._last_training
                else None
            )
            attrs["solar_model_trained"] = (
                self._ai_trainer.solar_predictor is not None
                and self._ai_trainer.solar_predictor.is_trained
            )
            attrs["load_model_trained"] = (
                self._ai_trainer.load_forecaster is not None
                and self._ai_trainer.load_forecaster.is_trained
            )
            attrs["decision_model_trained"] = (
                self._ai_trainer.decision_optimizer is not None
                and self._ai_trainer.decision_optimizer.is_trained
            )
        return attrs
```

**Step 2: Add to async_setup_entry in sensor.py**

```python
# Add AI status sensor if trainer available
ai_trainer = hass.data[DOMAIN][config_entry.entry_id].get("ai_trainer")
if ai_trainer:
    entities.append(AIStatusSensor(coordinator, config_entry, ai_trainer))
```

**Step 3: Commit**

```bash
git add custom_components/battery_energy_trading/sensor.py
git commit -m "feat(ai): add AI status sensor"
```

---

## Final Task: Update Models Init and Documentation

### Task 7.1: Update Module Exports

**Files:**
- Modify: `custom_components/battery_energy_trading/ai/models/__init__.py`

```python
"""AI models for battery energy trading."""
from __future__ import annotations

from .base import BaseModel
from .decision_optimizer import Action, DecisionOptimizer
from .load_forecaster import LoadForecaster
from .solar_predictor import SolarPredictor

__all__ = [
    "Action",
    "BaseModel",
    "DecisionOptimizer",
    "LoadForecaster",
    "SolarPredictor",
]
```

### Task 7.2: Final Commit

```bash
git add -A
git commit -m "feat(ai): complete AI smart battery management foundation

- Data extraction from HA Long-Term Statistics
- Feature engineering for solar, load, and decisions
- Solar predictor with Forecast.Solar correction
- Load forecaster with heat pump stage modeling
- Q-learning decision optimizer (Nord Pool prices PRIMARY)
- Training orchestrator with memory management
- AI services for manual training control
- AI status sensor for monitoring

Phase 1 of 6 complete. Ready for testing and refinement."
```

---

## Testing Commands

```bash
# Run all AI tests
pytest tests/test_ai_*.py tests/test_*_predictor.py tests/test_*_forecaster.py tests/test_*_optimizer.py -v

# Run with coverage
pytest tests/ --cov=custom_components.battery_energy_trading.ai --cov-report=html

# Verify all existing tests still pass
pytest tests/ -v
```

---

Plan complete and saved to `docs/plans/2025-12-02-ai-smart-battery-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session in worktree with executing-plans, batch execution with checkpoints

Which approach?
