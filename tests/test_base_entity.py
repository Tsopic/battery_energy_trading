"""Tests for base_entity.py helper methods."""
import pytest
from unittest.mock import MagicMock, Mock
from datetime import datetime

from custom_components.battery_energy_trading.base_entity import (
    BatteryTradingBaseEntity,
)
from custom_components.battery_energy_trading.const import DOMAIN, VERSION


class TestBatteryTradingBaseEntity:
    """Test BatteryTradingBaseEntity class."""

    @pytest.fixture
    def base_entity(self, mock_hass, mock_config_entry):
        """Create a base entity instance for testing."""
        return BatteryTradingBaseEntity(
            hass=mock_hass,
            entry=mock_config_entry,
            entity_type="test_entity",
        )

    def test_init(self, base_entity, mock_hass, mock_config_entry):
        """Test base entity initialization."""
        assert base_entity.hass == mock_hass
        assert base_entity._entry == mock_config_entry
        assert base_entity._entity_type == "test_entity"
        assert (
            base_entity._attr_unique_id
            == f"{DOMAIN}_{mock_config_entry.entry_id}_test_entity"
        )
        assert base_entity._attr_has_entity_name is True

    def test_device_info(self, base_entity, mock_config_entry):
        """Test device info generation."""
        device_info = base_entity._attr_device_info
        assert device_info["identifiers"] == {(DOMAIN, mock_config_entry.entry_id)}
        assert device_info["name"] == "Battery Energy Trading"
        assert device_info["manufacturer"] == "Battery Energy Trading"
        assert device_info["model"] == "Energy Optimizer"
        assert device_info["sw_version"] == VERSION

    def test_unique_id_format(self, base_entity):
        """Test unique ID follows expected format."""
        unique_id = base_entity._attr_unique_id
        assert unique_id.startswith(DOMAIN)
        assert "_test_entry_id_" in unique_id
        assert unique_id.endswith("test_entity")


class TestGetFloatState:
    """Test _get_float_state method."""

    @pytest.fixture
    def base_entity(self, mock_hass, mock_config_entry):
        """Create a base entity instance."""
        return BatteryTradingBaseEntity(
            hass=mock_hass, entry=mock_config_entry, entity_type="test"
        )

    def test_get_float_state_valid(self, base_entity, mock_hass):
        """Test getting valid float state."""
        # Setup mock state
        mock_state = MagicMock()
        mock_state.state = "75.5"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_float_state("sensor.test_entity")
        assert result == 75.5

    def test_get_float_state_none_entity_id(self, base_entity):
        """Test with None entity_id returns default."""
        result = base_entity._get_float_state(None, default=42.0)
        assert result == 42.0

    def test_get_float_state_empty_entity_id(self, base_entity):
        """Test with empty string entity_id returns default."""
        result = base_entity._get_float_state("", default=10.0)
        assert result == 10.0

    def test_get_float_state_entity_not_found(self, base_entity, mock_hass):
        """Test when entity doesn't exist."""
        mock_hass.states.get = Mock(return_value=None)

        result = base_entity._get_float_state("sensor.missing", default=99.9)
        assert result == 99.9

    def test_get_float_state_unknown_state(self, base_entity, mock_hass):
        """Test when entity state is 'unknown'."""
        mock_state = MagicMock()
        mock_state.state = "unknown"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_float_state("sensor.unknown", default=5.0)
        assert result == 5.0

    def test_get_float_state_unavailable_state(self, base_entity, mock_hass):
        """Test when entity state is 'unavailable'."""
        mock_state = MagicMock()
        mock_state.state = "unavailable"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_float_state("sensor.unavailable", default=3.0)
        assert result == 3.0

    def test_get_float_state_invalid_conversion(self, base_entity, mock_hass):
        """Test when state cannot be converted to float."""
        mock_state = MagicMock()
        mock_state.state = "not_a_number"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_float_state("sensor.invalid", default=12.5)
        assert result == 12.5

    def test_get_float_state_integer_value(self, base_entity, mock_hass):
        """Test conversion of integer state."""
        mock_state = MagicMock()
        mock_state.state = "100"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_float_state("sensor.integer")
        assert result == 100.0
        assert isinstance(result, float)

    def test_get_float_state_negative_value(self, base_entity, mock_hass):
        """Test negative float values."""
        mock_state = MagicMock()
        mock_state.state = "-15.7"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_float_state("sensor.negative")
        assert result == -15.7

    def test_get_float_state_zero(self, base_entity, mock_hass):
        """Test zero value."""
        mock_state = MagicMock()
        mock_state.state = "0"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_float_state("sensor.zero")
        assert result == 0.0

    def test_get_float_state_type_error(self, base_entity, mock_hass):
        """Test when state.state raises TypeError."""
        mock_state = MagicMock()
        mock_state.state = None  # Will raise TypeError on float()
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_float_state("sensor.type_error", default=7.5)
        assert result == 7.5


class TestGetSwitchState:
    """Test _get_switch_state method."""

    @pytest.fixture
    def base_entity(self, mock_hass, mock_config_entry):
        """Create a base entity instance."""
        return BatteryTradingBaseEntity(
            hass=mock_hass, entry=mock_config_entry, entity_type="test"
        )

    def test_get_switch_state_on(self, base_entity, mock_hass):
        """Test switch in 'on' state."""
        mock_state = MagicMock()
        mock_state.state = "on"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_switch_state("enable_something")
        assert result is True

    def test_get_switch_state_off(self, base_entity, mock_hass):
        """Test switch in 'off' state."""
        mock_state = MagicMock()
        mock_state.state = "off"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_switch_state("enable_something")
        assert result is False

    def test_get_switch_state_not_found_defaults_true(self, base_entity, mock_hass):
        """Test missing switch defaults to True (enabled)."""
        mock_hass.states.get = Mock(return_value=None)

        result = base_entity._get_switch_state("missing_switch")
        assert result is True

    def test_get_switch_state_entity_id_format(self, base_entity, mock_hass):
        """Test correct entity_id construction."""
        mock_hass.states.get = Mock(return_value=None)

        base_entity._get_switch_state("test_switch")

        expected_entity_id = f"switch.{DOMAIN}_test_entry_id_test_switch"
        mock_hass.states.get.assert_called_once_with(expected_entity_id)

    def test_get_switch_state_exception_defaults_true(self, base_entity, mock_hass):
        """Test exception during switch state retrieval defaults to True."""
        mock_hass.states.get = Mock(side_effect=Exception("Test error"))

        result = base_entity._get_switch_state("error_switch")
        assert result is True

    def test_get_switch_state_unknown_state(self, base_entity, mock_hass):
        """Test switch with 'unknown' state."""
        mock_state = MagicMock()
        mock_state.state = "unknown"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_switch_state("unknown_switch")
        assert result is False  # 'unknown' != 'on'

    def test_get_switch_state_unavailable_state(self, base_entity, mock_hass):
        """Test switch with 'unavailable' state."""
        mock_state = MagicMock()
        mock_state.state = "unavailable"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_switch_state("unavailable_switch")
        assert result is False  # 'unavailable' != 'on'


class TestGetNumberEntityValue:
    """Test _get_number_entity_value method."""

    @pytest.fixture
    def base_entity(self, mock_hass, mock_config_entry):
        """Create a base entity instance."""
        return BatteryTradingBaseEntity(
            hass=mock_hass, entry=mock_config_entry, entity_type="test"
        )

    def test_get_number_entity_value_valid(self, base_entity, mock_hass):
        """Test getting valid number entity value."""
        mock_state = MagicMock()
        mock_state.state = "50.5"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_number_entity_value("test_number", default=10.0)
        assert result == 50.5

    def test_get_number_entity_value_not_found(self, base_entity, mock_hass):
        """Test number entity not found returns default."""
        mock_hass.states.get = Mock(return_value=None)

        result = base_entity._get_number_entity_value("missing_number", default=25.0)
        assert result == 25.0

    def test_get_number_entity_value_entity_id_format(self, base_entity, mock_hass):
        """Test correct entity_id construction for number entities."""
        mock_hass.states.get = Mock(return_value=None)

        base_entity._get_number_entity_value("min_price", default=0.0)

        expected_entity_id = f"number.{DOMAIN}_test_entry_id_min_price"
        mock_hass.states.get.assert_called_once_with(expected_entity_id)

    def test_get_number_entity_value_zero(self, base_entity, mock_hass):
        """Test number entity with zero value."""
        mock_state = MagicMock()
        mock_state.state = "0"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_number_entity_value("zero_number", default=5.0)
        assert result == 0.0

    def test_get_number_entity_value_negative(self, base_entity, mock_hass):
        """Test number entity with negative value."""
        mock_state = MagicMock()
        mock_state.state = "-0.5"
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._get_number_entity_value("negative_number", default=0.0)
        assert result == -0.5


class TestSafeGetAttribute:
    """Test _safe_get_attribute method."""

    @pytest.fixture
    def base_entity(self, mock_hass, mock_config_entry):
        """Create a base entity instance."""
        return BatteryTradingBaseEntity(
            hass=mock_hass, entry=mock_config_entry, entity_type="test"
        )

    def test_safe_get_attribute_found(self, base_entity, mock_hass):
        """Test getting existing attribute."""
        mock_state = MagicMock()
        mock_state.attributes = {"test_attr": "test_value"}
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._safe_get_attribute(
            "sensor.test", "test_attr", default="default"
        )
        assert result == "test_value"

    def test_safe_get_attribute_not_found(self, base_entity, mock_hass):
        """Test attribute not found returns default."""
        mock_state = MagicMock()
        mock_state.attributes = {}
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._safe_get_attribute(
            "sensor.test", "missing_attr", default="default_value"
        )
        assert result == "default_value"

    def test_safe_get_attribute_entity_not_found(self, base_entity, mock_hass):
        """Test entity not found returns default."""
        mock_hass.states.get = Mock(return_value=None)

        result = base_entity._safe_get_attribute(
            "sensor.missing", "any_attr", default=None
        )
        assert result is None

    def test_safe_get_attribute_complex_value(self, base_entity, mock_hass):
        """Test getting complex attribute value (list)."""
        mock_state = MagicMock()
        mock_state.attributes = {
            "raw_today": [
                {"start": datetime(2025, 10, 1, 0, 0), "value": 0.15},
                {"start": datetime(2025, 10, 1, 1, 0), "value": 0.12},
            ]
        }
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._safe_get_attribute(
            "sensor.nordpool", "raw_today", default=[]
        )
        assert len(result) == 2
        assert result[0]["value"] == 0.15

    def test_safe_get_attribute_none_default(self, base_entity, mock_hass):
        """Test default None when attribute missing."""
        mock_state = MagicMock()
        mock_state.attributes = {}
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._safe_get_attribute("sensor.test", "attr")
        assert result is None

    def test_safe_get_attribute_exception_returns_default(self, base_entity, mock_hass):
        """Test exception during attribute retrieval returns default."""
        mock_hass.states.get = Mock(side_effect=Exception("Test error"))

        result = base_entity._safe_get_attribute(
            "sensor.error", "attr", default="safe_default"
        )
        assert result == "safe_default"

    def test_safe_get_attribute_dict_value(self, base_entity, mock_hass):
        """Test getting dict attribute value."""
        mock_state = MagicMock()
        mock_state.attributes = {
            "device_info": {
                "manufacturer": "Sungrow",
                "model": "SH10RT",
            }
        }
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._safe_get_attribute(
            "sensor.inverter", "device_info", default={}
        )
        assert result["manufacturer"] == "Sungrow"
        assert result["model"] == "SH10RT"

    def test_safe_get_attribute_boolean_value(self, base_entity, mock_hass):
        """Test getting boolean attribute value."""
        mock_state = MagicMock()
        mock_state.attributes = {"auto_detected": True}
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._safe_get_attribute(
            "sensor.config", "auto_detected", default=False
        )
        assert result is True

    def test_safe_get_attribute_numeric_value(self, base_entity, mock_hass):
        """Test getting numeric attribute value."""
        mock_state = MagicMock()
        mock_state.attributes = {"capacity": 12.8}
        mock_hass.states.get = Mock(return_value=mock_state)

        result = base_entity._safe_get_attribute(
            "sensor.battery", "capacity", default=0.0
        )
        assert result == 12.8
