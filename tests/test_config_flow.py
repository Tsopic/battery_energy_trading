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
    async def test_user_step_no_sungrow(self, mock_hass):
        """Test user step when no Sungrow integration."""
        mock_hass.states.async_all = Mock(return_value=[])

        flow = ConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "manual"

    @pytest.mark.asyncio
    async def test_user_step_with_sungrow(self, mock_hass, mock_sungrow_entities):
        """Test user step when Sungrow integration is detected."""
        mock_hass.states.async_all = Mock(return_value=mock_sungrow_entities)

        flow = ConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "sungrow_detect"

    @pytest.mark.asyncio
    async def test_sungrow_detect_accept_auto(self, mock_hass, mock_sungrow_entities):
        """Test accepting Sungrow auto-detection."""
        mock_hass.states.async_all = Mock(return_value=mock_sungrow_entities)

        flow = ConfigFlow()
        flow.hass = mock_hass

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
    async def test_manual_config_success(self, mock_hass):
        """Test successful manual configuration."""
        # Mock that entities exist
        mock_hass.states.get = Mock(return_value=MagicMock())

        flow = ConfigFlow()
        flow.hass = mock_hass

        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
            CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
            CONF_BATTERY_CAPACITY_ENTITY: "sensor.battery_capacity",
            CONF_SOLAR_POWER_ENTITY: "sensor.solar_power",
        }

        result = await flow.async_step_manual(user_input=user_input)

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
    async def test_sungrow_auto_config_success(self, mock_hass, mock_sungrow_entities):
        """Test successful Sungrow auto-configuration."""
        mock_hass.states.async_all = Mock(return_value=mock_sungrow_entities)
        mock_hass.states.get = Mock(side_effect=lambda entity_id: next(
            (e for e in mock_sungrow_entities if e.entity_id == entity_id), Mock()
        ))

        flow = ConfigFlow()
        flow.hass = mock_hass

        # First get to the sungrow_auto step
        await flow.async_step_sungrow_auto()

        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
            CONF_BATTERY_LEVEL_ENTITY: "sensor.sungrow_battery_level",
            CONF_BATTERY_CAPACITY_ENTITY: "sensor.sungrow_battery_capacity",
            CONF_SOLAR_POWER_ENTITY: "sensor.sungrow_pv_power",
        }

        result = await flow.async_step_sungrow_auto(user_input=user_input)

        assert result["type"] == "create_entry"
        assert result["title"] == "Battery Energy Trading (Sungrow)"
        assert result["data"] == user_input
        # Check that options contain auto-detected rates
        assert "options" in result
        assert result["options"]["auto_detected"] is True
        assert result["options"]["charge_rate"] == 10.0  # SH10RT default
        assert result["options"]["discharge_rate"] == 10.0

    @pytest.mark.asyncio
    async def test_sungrow_auto_config_shows_detected_values(self, mock_hass, mock_sungrow_entities):
        """Test that Sungrow auto form shows detected values as defaults."""
        mock_hass.states.async_all = Mock(return_value=mock_sungrow_entities)

        flow = ConfigFlow()
        flow.hass = mock_hass

        result = await flow.async_step_sungrow_auto()

        assert result["type"] == "form"
        assert result["step_id"] == "sungrow_auto"

        # Check description includes detected info
        assert "description_placeholders" in result
        assert "detected_info" in result["description_placeholders"]

    @pytest.mark.asyncio
    async def test_manual_config_optional_solar(self, mock_hass):
        """Test manual configuration without solar sensor."""
        mock_hass.states.get = Mock(return_value=MagicMock())

        flow = ConfigFlow()
        flow.hass = mock_hass

        user_input = {
            CONF_NORDPOOL_ENTITY: "sensor.nordpool_kwh_ee_eur_3_10_022",
            CONF_BATTERY_LEVEL_ENTITY: "sensor.battery_level",
            CONF_BATTERY_CAPACITY_ENTITY: "sensor.battery_capacity",
            # No solar power entity
        }

        result = await flow.async_step_manual(user_input=user_input)

        assert result["type"] == "create_entry"
        assert CONF_SOLAR_POWER_ENTITY not in result["data"] or result["data"][CONF_SOLAR_POWER_ENTITY] is None
