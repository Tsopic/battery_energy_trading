"""Tests for base model interface."""
import numpy as np
import pytest

from custom_components.battery_energy_trading.ai.models.base import BaseModel


class TestBaseModel:
    """Test base model interface."""

    def test_cannot_instantiate_base(self) -> None:
        """Test that BaseModel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseModel("test")  # type: ignore

    def test_subclass_must_implement_methods(self) -> None:
        """Test that subclass must implement abstract methods."""

        class IncompleteModel(BaseModel):
            pass

        with pytest.raises(TypeError):
            IncompleteModel("incomplete")  # type: ignore

    def test_complete_subclass_can_instantiate(self) -> None:
        """Test that complete subclass can be instantiated."""
        from pathlib import Path

        class CompleteModel(BaseModel):
            def train(
                self, X: np.ndarray, y: np.ndarray
            ) -> dict[str, float]:
                self._is_trained = True
                return {"mse": 0.0}

            def predict(self, X: np.ndarray) -> np.ndarray:
                return np.zeros(len(X))

            def save(self, path: Path) -> None:
                pass

            def load(self, path: Path) -> None:
                self._is_trained = True

        model = CompleteModel("test_model")
        assert model.name == "test_model"
        assert model.is_trained is False

    def test_is_trained_property(self) -> None:
        """Test is_trained property updates after training."""
        from pathlib import Path

        class TrainableModel(BaseModel):
            def train(
                self, X: np.ndarray, y: np.ndarray
            ) -> dict[str, float]:
                self._is_trained = True
                return {"mse": 0.01}

            def predict(self, X: np.ndarray) -> np.ndarray:
                return np.zeros(len(X))

            def save(self, path: Path) -> None:
                pass

            def load(self, path: Path) -> None:
                self._is_trained = True

        model = TrainableModel("trainable")
        assert model.is_trained is False

        X = np.random.randn(100, 5)
        y = np.random.randn(100)
        model.train(X, y)

        assert model.is_trained is True

    def test_export_onnx_not_implemented(self) -> None:
        """Test ONNX export raises NotImplementedError by default."""
        from pathlib import Path

        class SimpleModel(BaseModel):
            def train(
                self, X: np.ndarray, y: np.ndarray
            ) -> dict[str, float]:
                return {}

            def predict(self, X: np.ndarray) -> np.ndarray:
                return np.zeros(len(X))

            def save(self, path: Path) -> None:
                pass

            def load(self, path: Path) -> None:
                pass

        model = SimpleModel("simple")
        with pytest.raises(NotImplementedError):
            model.export_onnx(Path("/tmp"), (10,))

    def test_get_feature_importance_returns_none(self) -> None:
        """Test feature importance returns None by default."""
        from pathlib import Path

        class SimpleModel(BaseModel):
            def train(
                self, X: np.ndarray, y: np.ndarray
            ) -> dict[str, float]:
                return {}

            def predict(self, X: np.ndarray) -> np.ndarray:
                return np.zeros(len(X))

            def save(self, path: Path) -> None:
                pass

            def load(self, path: Path) -> None:
                pass

        model = SimpleModel("simple")
        assert model.get_feature_importance() is None
