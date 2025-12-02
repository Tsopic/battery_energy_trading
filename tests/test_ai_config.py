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

    def test_model_configuration_defaults(self) -> None:
        """Test model configuration defaults."""
        config = AIConfig()
        assert config.solar_model_estimators == 50
        assert config.solar_model_max_depth == 5
        assert config.q_learning_rate == 0.1
        assert config.q_discount_factor == 0.95

    def test_training_schedule_default(self) -> None:
        """Test training schedule default (Sunday 03:00)."""
        config = AIConfig()
        assert config.training_schedule == "0 3 * * 0"
