"""Pytest configuration and fixtures for Battery Energy Trading tests."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.async_all = Mock(return_value=[])
    hass.states.get = Mock(return_value=None)
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "nordpool_entity": "sensor.nordpool_kwh_ee_eur_3_10_022",
        "battery_level_entity": "sensor.battery_level",
        "battery_capacity_entity": "sensor.battery_capacity",
        "solar_power_entity": "sensor.solar_power",
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_config_entry_sungrow():
    """Mock config entry with Sungrow auto-detection."""
    entry = MagicMock()
    entry.entry_id = "test_sungrow_entry"
    entry.data = {
        "nordpool_entity": "sensor.nordpool_kwh_ee_eur_3_10_022",
        "battery_level_entity": "sensor.sungrow_battery_level",
        "battery_capacity_entity": "sensor.sungrow_battery_capacity",
        "solar_power_entity": "sensor.sungrow_pv_power",
    }
    entry.options = {
        "charge_rate": 10.0,
        "discharge_rate": 10.0,
        "inverter_model": "SH10RT",
        "auto_detected": True,
    }
    return entry


@pytest.fixture
def sample_price_data():
    """Sample 15-minute price data for testing."""
    base_time = datetime(2025, 10, 1, 0, 0, 0)
    prices = []

    # Create 24 hours of 15-minute slots (96 slots)
    for hour in range(24):
        for quarter in range(4):
            start = base_time + timedelta(hours=hour, minutes=quarter * 15)
            end = start + timedelta(minutes=15)

            # Vary prices throughout the day
            if 8 <= hour < 10:  # Morning peak
                price = 0.35 + (quarter * 0.02)
            elif 17 <= hour < 20:  # Evening peak
                price = 0.40 + (quarter * 0.03)
            elif 2 <= hour < 5:  # Night cheap
                price = -0.01 + (quarter * 0.01)
            else:  # Normal hours
                price = 0.12 + (quarter * 0.01)

            prices.append({
                "start": start,
                "end": end,
                "value": price,
            })

    return prices


@pytest.fixture
def mock_sungrow_entities():
    """Mock Sungrow entities."""
    battery_level = MagicMock()
    battery_level.entity_id = "sensor.sungrow_battery_level"
    battery_level.state = "75"
    battery_level.attributes = {}

    battery_capacity = MagicMock()
    battery_capacity.entity_id = "sensor.sungrow_battery_capacity"
    battery_capacity.state = "12.8"
    battery_capacity.attributes = {"model": "SBR128"}

    pv_power = MagicMock()
    pv_power.entity_id = "sensor.sungrow_pv_power"
    pv_power.state = "2500"
    pv_power.attributes = {}

    device_type = MagicMock()
    device_type.entity_id = "sensor.sungrow_device_type_code"
    device_type.state = "SH10RT"
    device_type.attributes = {}

    return [battery_level, battery_capacity, pv_power, device_type]
