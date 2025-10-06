"""Tests for config flow."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.battery_energy_trading.config_flow import ConfigFlow
from custom_components.battery_energy_trading.const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    CONF_BATTERY_LEVEL_ENTITY,
    CONF_BATTERY_CAPACITY_ENTITY,
    CONF_SOLAR_POWER_ENTITY,
)


class TestConfigFlow:
    """Tests for Battery Energy Trading config flow."""

    @pytest.mark.asyncio
    async def test_user_step_no_sungrow(self, mock_hass_with_nordpool):
        """Test user step when no Sungrow integration."""
        # Only Nord Pool entities, no Sungrow
        flow = ConfigFlow()
        flow.hass = mock_hass_with_nordpool

        result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "manual"

    @pytest.mark.asyncio
    async def test_user_step_with_sungrow(self, mock_hass_with_nordpool_and_sungrow):
        """Test user step when Sungrow integration is detected."""
        flow = ConfigFlow()
        flow.hass = mock_hass_with_nordpool_and_sungrow

        result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "sungrow_detect"

    @pytest.mark.asyncio
    async def test_sungrow_detect_accept_auto(self, mock_hass_with_nordpool_and_sungrow):
        """Test accepting Sungrow auto-detection."""
        flow = ConfigFlow()
        flow.hass = mock_hass_with_nordpool_and_sungrow

        result = await flow.async_step_sungrow_detect(
            user_input={"use_auto_detection": True}
        )

        assert result["type"] == "form"
        assert result["step_id"] == "sungrow_auto"

    @pytest.mark.asyncio
    async def test_sungrow_detect_decline_auto(self, mock_hass):
        """Test declining Sungrow auto-detection."""
        flow = ConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_sungrow_detect(
            user_input={"use_auto_detection": False}
        )

        assert result["type"] == "form"
        assert result["step_id"] == "manual"

    @pytest.mark.asyncio
    async def test_manual_config_success(self, mock_hass_with_nordpool):
        """Test successful manual configuration."""
        # Create mock entities for battery and solar
        battery_level = MagicMock()
        battery_level.entity_id = "sensor.battery_level"
        battery_level.state = "75"
        battery_level.attributes = {}

        battery_capacity = MagicMock()
        battery_capacity.entity_id = "sensor.battery_capacity"
        battery_capacity.state = "12.8"
        battery_capacity.attributes = {}

        solar_power = MagicMock()
        solar_power.entity_id = "sensor.solar_power"
        solar_power.state = "2500"
        solar_power.attributes = {}

        # Update mock to return these entities
        original_get = mock_hass_with_nordpool.states.get

        def get_state(entity_id):
            if entity_id == "sensor.battery_level":
                return battery_level
            elif entity_id == "sensor.battery_capacity":
                return battery_capacity
            elif entity_id == "sensor.solar_power":
                return solar_power
            return original_get(entity_id)

        mock_hass_with_nordpool.states.get = Mock(side_effect=get_state)

        flow = ConfigFlow()
        flow.hass = mock_hass_with_nordpool

        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
            CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
            CONF_BATTERY_CAPACITY_ENTITY: "sensor.battery_capacity",
            CONF_SOLAR_POWER_ENTITY: "sensor.solar_power",
        }

        result = await flow.async_step_manual(user_input=user_input)

        # Should redirect to dashboard step
        assert result["type"] == "form"
        assert result["step_id"] == "dashboard"

        # Complete dashboard step to create entry
        result = await flow.async_step_dashboard(user_input={})

        assert result["type"] == "create_entry"
        assert result["title"] == "Battery Energy Trading"
        assert result["data"] == user_input

    @pytest.mark.asyncio
    async def test_manual_config_entity_not_found(self, mock_hass):
        """Test manual configuration with non-existent entity."""
        # Mock that entities don't exist
        mock_hass.states.get = Mock(return_value=None)

        flow = ConfigFlow()
        flow.hass = mock_hass

        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.nonexistent",
            CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
            CONF_BATTERY_CAPACITY_ENTITY: "sensor.battery_capacity",
        }

        result = await flow.async_step_manual(user_input=user_input)

        assert result["type"] == "form"
        assert "errors" in result
        assert CONF_NORDPOOL_ENTITY in result["errors"]

    @pytest.mark.asyncio
    async def test_sungrow_auto_config_success(self, mock_hass_with_nordpool_and_sungrow):
        """Test successful Sungrow auto-configuration."""
        flow = ConfigFlow()
        flow.hass = mock_hass_with_nordpool_and_sungrow

        # First get to the sungrow_auto step
        await flow.async_step_sungrow_auto()

        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
            CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
            CONF_BATTERY_CAPACITY_ENTITY: "sensor.battery_capacity",
            CONF_SOLAR_POWER_ENTITY: "sensor.total_dc_power",
        }

        result = await flow.async_step_sungrow_auto(user_input=user_input)

        # Should redirect to dashboard step
        assert result["type"] == "form"
        assert result["step_id"] == "dashboard"

        # Complete dashboard step to create entry
        result = await flow.async_step_dashboard(user_input={})

        assert result["type"] == "create_entry"
        assert result["title"] == "Battery Energy Trading (Sungrow)"
        assert result["data"] == user_input
        # Check that options contain auto-detected rates
        assert "options" in result
        assert result["options"]["auto_detected"] is True
        assert result["options"]["charge_rate"] == 10.0  # SH10RT default
        assert result["options"]["discharge_rate"] == 10.0

    @pytest.mark.asyncio
    async def test_sungrow_auto_config_shows_detected_values(self, mock_hass_with_nordpool_and_sungrow):
        """Test that Sungrow auto form shows detected values as defaults."""
        flow = ConfigFlow()
        flow.hass = mock_hass_with_nordpool_and_sungrow

        result = await flow.async_step_sungrow_auto()

        assert result["type"] == "form"
        assert result["step_id"] == "sungrow_auto"

        # Check description includes detected info
        assert "description_placeholders" in result
        assert "detected_info" in result["description_placeholders"]

    @pytest.mark.asyncio
    async def test_manual_config_optional_solar(self, mock_hass_with_nordpool):
        """Test manual configuration without solar sensor."""
        # Create mock entities for battery (no solar)
        battery_level = MagicMock()
        battery_level.entity_id = "sensor.battery_level"
        battery_level.state = "75"
        battery_level.attributes = {}

        battery_capacity = MagicMock()
        battery_capacity.entity_id = "sensor.battery_capacity"
        battery_capacity.state = "12.8"
        battery_capacity.attributes = {}

        # Update mock to return these entities
        original_get = mock_hass_with_nordpool.states.get

        def get_state(entity_id):
            if entity_id == "sensor.battery_level":
                return battery_level
            elif entity_id == "sensor.battery_capacity":
                return battery_capacity
            return original_get(entity_id)

        mock_hass_with_nordpool.states.get = Mock(side_effect=get_state)

        flow = ConfigFlow()
        flow.hass = mock_hass_with_nordpool

        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
            CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
            CONF_BATTERY_CAPACITY_ENTITY: "sensor.battery_capacity",
            # No solar power entity
        }

        result = await flow.async_step_manual(user_input=user_input)

        # Should redirect to dashboard step
        assert result["type"] == "form"
        assert result["step_id"] == "dashboard"

        # Complete dashboard step to create entry
        result = await flow.async_step_dashboard(user_input={})

        assert result["type"] == "create_entry"
        assert CONF_SOLAR_POWER_ENTITY not in result["data"] or result["data"][CONF_SOLAR_POWER_ENTITY] is None
