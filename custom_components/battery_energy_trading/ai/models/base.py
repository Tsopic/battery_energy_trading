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
