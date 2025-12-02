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
from .models import (
    Action,
    BaseModel,
    DecisionOptimizer,
    LoadForecaster,
    SolarPredictor,
)
from .training import AITrainer


__all__ = [
    # Config and data
    "AIConfig",
    "DataExtractor",
    "FeatureEngineering",
    # Feature functions
    "create_lag_features",
    "create_rolling_features",
    "create_time_features",
    # Models
    "Action",
    "BaseModel",
    "DecisionOptimizer",
    "LoadForecaster",
    "SolarPredictor",
    # Training
    "AITrainer",
]
