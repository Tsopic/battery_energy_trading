"""Tests for Sungrow helper module."""
import pytest
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.battery_energy_trading.sungrow_helper import SungrowHelper


class TestSungrowHelper:
    """Tests for SungrowHelper class."""

    def test_detect_sungrow_entities(self, mock_hass, mock_sungrow_entities):
        """Test Sungrow entity detection with actual Modbus entity names."""
        mock_hass.states.async_all = Mock(return_value=mock_sungrow_entities)

        helper = SungrowHelper(mock_hass)
        detected = helper.detect_sungrow_entities()

        # Actual Sungrow Modbus integration entity names
        assert detected["battery_level"] == "sensor.battery_level"
        assert detected["battery_capacity"] == "sensor.battery_capacity"
        assert detected["solar_power"] == "sensor.total_dc_power"
        assert detected["device_type"] == "sensor.sungrow_device_type"

    def test_detect_sungrow_entities_no_sungrow(self, mock_hass):
        """Test entity detection with no Sungrow integration."""
        # Mock non-Sungrow entities with names that don't match Sungrow patterns
        other_entities = [
            Mock(entity_id="sensor.tesla_battery_soc"),  # Tesla battery, not Sungrow
            Mock(entity_id="sensor.solar_production_total"),  # Generic solar, not Sungrow
            Mock(entity_id="sensor.home_battery_capacity_kwh"),  # Generic capacity
        ]
        mock_hass.states.async_all = Mock(return_value=other_entities)

        helper = SungrowHelper(mock_hass)
        detected = helper.detect_sungrow_entities()

        assert detected["battery_level"] is None
        assert detected["battery_capacity"] is None
        assert detected["solar_power"] is None

    def test_get_inverter_specs_sh10rt(self, mock_hass):
        """Test inverter specs lookup for SH10RT."""
        helper = SungrowHelper(mock_hass)

        specs = helper.get_inverter_specs("SH10RT")
        assert specs is not None
        assert specs["max_charge_kw"] == 10.0
        assert specs["max_discharge_kw"] == 10.0

    def test_get_inverter_specs_sh5rt(self, mock_hass):
        """Test inverter specs lookup for SH5.0RT."""
        helper = SungrowHelper(mock_hass)

        specs = helper.get_inverter_specs("SH5.0RT")
        assert specs is not None
        assert specs["max_charge_kw"] == 5.0
        assert specs["max_discharge_kw"] == 5.0

    def test_get_inverter_specs_with_version(self, mock_hass):
        """Test inverter specs with version suffix."""
        helper = SungrowHelper(mock_hass)

        # Should still match even with version info
        specs = helper.get_inverter_specs("SH10RT V1.1.2")
        assert specs is not None
        assert specs["max_charge_kw"] == 10.0

    def test_get_inverter_specs_unknown_model(self, mock_hass):
        """Test unknown inverter model."""
        helper = SungrowHelper(mock_hass)

        specs = helper.get_inverter_specs("UNKNOWN_MODEL")
        assert specs is None

    def test_get_inverter_specs_case_insensitive(self, mock_hass):
        """Test case-insensitive model matching."""
        helper = SungrowHelper(mock_hass)

        specs = helper.get_inverter_specs("sh10rt")
        assert specs is not None
        assert specs["max_charge_kw"] == 10.0

    def test_detect_inverter_model_from_device_type_sensor(self, mock_hass, mock_sungrow_entities):
        """Test inverter model detection from device type sensor."""
        mock_hass.states.async_all = Mock(return_value=mock_sungrow_entities)

        helper = SungrowHelper(mock_hass)
        model = helper.detect_inverter_model_from_entities()

        assert model == "SH10RT"

    def test_detect_inverter_model_from_entity_id(self, mock_hass):
        """Test inverter model detection from entity ID."""
        entity = Mock()
        entity.entity_id = "sensor.sh10rt_battery_level"
        entity.state = "75"
        entity.attributes = {}

        mock_hass.states.async_all = Mock(return_value=[entity])

        helper = SungrowHelper(mock_hass)
        model = helper.detect_inverter_model_from_entities()

        assert model == "SH10RT"

    def test_detect_inverter_model_from_attributes(self, mock_hass):
        """Test inverter model detection from entity attributes."""
        entity = Mock()
        entity.entity_id = "sensor.sungrow_battery_level"
        entity.state = "75"
        entity.attributes = {"model": "SH10RT"}

        mock_hass.states.async_all = Mock(return_value=[entity])

        helper = SungrowHelper(mock_hass)
        model = helper.detect_inverter_model_from_entities()

        assert model == "SH10RT"

    def test_is_sungrow_integration_available_true(self, mock_hass, mock_sungrow_entities):
        """Test Sungrow integration detection when available."""
        mock_hass.states.async_all = Mock(return_value=mock_sungrow_entities)

        helper = SungrowHelper(mock_hass)
        assert helper.is_sungrow_integration_available() is True

    def test_is_sungrow_integration_available_false(self, mock_hass):
        """Test Sungrow integration detection when not available."""
        # Use entity names that don't match Sungrow patterns
        other_entities = [
            Mock(entity_id="sensor.tesla_battery_soc"),
            Mock(entity_id="sensor.solar_production_total"),
        ]
        mock_hass.states.async_all = Mock(return_value=other_entities)

        helper = SungrowHelper(mock_hass)
        assert helper.is_sungrow_integration_available() is False

    @pytest.mark.asyncio
    async def test_async_get_auto_configuration_complete(self, mock_hass, mock_sungrow_entities):
        """Test complete auto-configuration with all Sungrow entities."""
        mock_hass.states.async_all = Mock(return_value=mock_sungrow_entities)
        mock_hass.states.get = Mock(side_effect=lambda entity_id: next(
            (e for e in mock_sungrow_entities if e.entity_id == entity_id), None
        ))

        helper = SungrowHelper(mock_hass)
        config = await helper.async_get_auto_configuration()

        assert config["inverter_model"] == "SH10RT"
        assert config["recommended_charge_rate"] == 10.0
        assert config["recommended_discharge_rate"] == 10.0
        assert config["battery_capacity"] == 12.8
        assert config["detected_entities"]["battery_level"] == "sensor.battery_level"

    @pytest.mark.asyncio
    async def test_async_get_auto_configuration_partial(self, mock_hass):
        """Test auto-configuration with partial Sungrow detection."""
        # Only battery level entity (actual Modbus entity name)
        entity = Mock()
        entity.entity_id = "sensor.battery_level"
        entity.state = "75"
        entity.attributes = {}

        mock_hass.states.async_all = Mock(return_value=[entity])

        helper = SungrowHelper(mock_hass)
        config = await helper.async_get_auto_configuration()

        # Should still have defaults
        assert config["recommended_charge_rate"] == 5.0  # Default
        assert config["recommended_discharge_rate"] == 5.0  # Default
        assert config["detected_entities"]["battery_level"] == "sensor.battery_level"
        assert config["detected_entities"]["battery_capacity"] is None

    @pytest.mark.asyncio
    async def test_async_get_auto_configuration_sh5rt(self, mock_hass):
        """Test auto-configuration detects SH5.0RT correctly."""
        entity = Mock()
        entity.entity_id = "sensor.sh5rt_battery_level"
        entity.state = "75"
        entity.attributes = {}

        mock_hass.states.async_all = Mock(return_value=[entity])

        helper = SungrowHelper(mock_hass)
        config = await helper.async_get_auto_configuration()

        assert config["inverter_model"] == "SH5RT"
        assert config["recommended_charge_rate"] == 5.0
        assert config["recommended_discharge_rate"] == 5.0
