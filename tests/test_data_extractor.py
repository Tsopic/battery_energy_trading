"""Tests for data extraction from Home Assistant statistics."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.battery_energy_trading.ai.config import AIConfig
from custom_components.battery_energy_trading.ai.data_extractor import DataExtractor

if TYPE_CHECKING:
    pass


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

    def test_get_statistics_entities(self, extractor: DataExtractor) -> None:
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
            "custom_components.battery_energy_trading.ai.data_extractor._get_recorder_instance",
            return_value=MagicMock(async_add_executor_job=AsyncMock(return_value={})),
        ):
            data = await extractor.extract_training_data(days=7)
            assert data is not None
            assert len(data) == 0

    def test_has_sufficient_data_true(self, extractor: DataExtractor) -> None:
        """Test sufficient data check passes with enough records."""
        # 30 days * 24 hours = 720 minimum records
        data = {
            "sensor.total_dc_power": [{"mean": 100}] * 800,
            "sensor.load_power": [{"mean": 200}] * 800,
            "sensor.battery_level": [{"mean": 50}] * 800,
        }
        assert extractor.has_sufficient_data(data) is True

    def test_has_sufficient_data_false_missing(self, extractor: DataExtractor) -> None:
        """Test sufficient data check fails with missing entity."""
        data = {
            "sensor.total_dc_power": [{"mean": 100}] * 800,
            # Missing load_power
            "sensor.battery_level": [{"mean": 50}] * 800,
        }
        assert extractor.has_sufficient_data(data) is False

    def test_has_sufficient_data_false_insufficient(
        self, extractor: DataExtractor
    ) -> None:
        """Test sufficient data check fails with too few records."""
        data = {
            "sensor.total_dc_power": [{"mean": 100}] * 100,  # Only 100 records
            "sensor.load_power": [{"mean": 200}] * 100,
            "sensor.battery_level": [{"mean": 50}] * 100,
        }
        assert extractor.has_sufficient_data(data) is False

    def test_has_sufficient_data_empty(self, extractor: DataExtractor) -> None:
        """Test sufficient data check fails with empty data."""
        assert extractor.has_sufficient_data({}) is False

    def test_extract_recent_data_method_exists(
        self, extractor: DataExtractor
    ) -> None:
        """Test extracting recent data method exists."""
        assert hasattr(extractor, "extract_recent_data")
