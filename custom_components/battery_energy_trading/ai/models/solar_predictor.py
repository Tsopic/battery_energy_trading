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
