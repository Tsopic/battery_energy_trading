"""Load forecasting model with heat pump awareness."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge

from .base import BaseModel


_LOGGER = logging.getLogger(__name__)


class LoadForecaster(BaseModel):
    """Load forecaster with heat pump stage modeling.

    Uses ensemble of models for robust predictions.
    Heat pump is modeled separately with temperature-based stages.
    """

    # Heat pump power stages (kW) by temperature threshold
    HEAT_PUMP_STAGES = {
        15: 0,  # Above 15°C: off
        10: 3,  # 10-15°C: 3kW
        5: 6,  # 5-10°C: 6kW
        0: 9,  # 0-5°C: 9kW
        -5: 12,  # -5-0°C: 12kW
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
        self._models: list[tuple[str, Any]] = []
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
        for _name, model in self._models:
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
        for threshold, stage in sorted(self.HEAT_PUMP_STAGES.items(), reverse=True):
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
        hp_load = np.array([self.predict_heat_pump_stage(t) * 1000 for t in temperatures])

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
