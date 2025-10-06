"""Pytest configuration and fixtures for Battery Energy Trading tests."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock


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
def mock_hass_with_nordpool(mock_hass, mock_nord_pool_state):
    """Mock Home Assistant instance with Nord Pool integration."""
    # Make async_all return Nord Pool entity
    mock_hass.states.async_all = Mock(return_value=[mock_nord_pool_state])

    # Make states.get return Nord Pool entity when queried
    def get_state(entity_id):
        if entity_id == mock_nord_pool_state.entity_id:
            return mock_nord_pool_state
        return None

    mock_hass.states.get = Mock(side_effect=get_state)
    return mock_hass


@pytest.fixture
def mock_hass_with_nordpool_and_sungrow(mock_hass, mock_nord_pool_state, mock_sungrow_entities):
    """Mock Home Assistant instance with both Nord Pool and Sungrow integrations."""
    # Combine Nord Pool and Sungrow entities
    all_entities = [mock_nord_pool_state] + mock_sungrow_entities
    mock_hass.states.async_all = Mock(return_value=all_entities)

    # Make states.get return correct entity when queried
    def get_state(entity_id):
        if entity_id == mock_nord_pool_state.entity_id:
            return mock_nord_pool_state
        for entity in mock_sungrow_entities:
            if entity.entity_id == entity_id:
                return entity
        return None

    mock_hass.states.get = Mock(side_effect=get_state)
    return mock_hass


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
    """Mock Sungrow Modbus entities (matching actual integration entity names)."""
    # Actual Sungrow Modbus entities don't have "sungrow_" prefix
    # They are named based on their function: battery_level, battery_capacity, total_dc_power
    battery_level = MagicMock()
    battery_level.entity_id = "sensor.battery_level"  # sg_battery_level (address 13022)
    battery_level.state = "75"
    battery_level.attributes = {}

    battery_capacity = MagicMock()
    battery_capacity.entity_id = "sensor.battery_capacity"  # sg_battery_capacity (address 5638)
    battery_capacity.state = "12.8"
    battery_capacity.attributes = {}

    solar_power = MagicMock()
    solar_power.entity_id = "sensor.total_dc_power"  # sg_total_dc_power (address 5016)
    solar_power.state = "2500"
    solar_power.attributes = {}

    device_type = MagicMock()
    device_type.entity_id = "sensor.sungrow_device_type"  # Template sensor based on device_type_code
    device_type.state = "SH10RT"
    device_type.attributes = {}

    return [battery_level, battery_capacity, solar_power, device_type]


@pytest.fixture
def mock_nord_pool_state():
    """Mock Nord Pool sensor state with realistic price data."""
    state = MagicMock()
    state.state = "0.15"
    state.entity_id = "sensor.nordpool_kwh_ee_eur_3_10_022"

    # Create realistic raw_today data
    base_time = datetime(2025, 10, 2, 0, 0, 0)
    raw_today = []
    for hour in range(24):
        for quarter in range(4):
            start = base_time + timedelta(hours=hour, minutes=quarter * 15)
            end = start + timedelta(minutes=15)

            # Realistic Estonian pricing pattern
            if 8 <= hour < 10:  # Morning peak
                price = 0.35 + (quarter * 0.02)
            elif 17 <= hour < 20:  # Evening peak
                price = 0.40 + (quarter * 0.03)
            elif 2 <= hour < 5:  # Night cheap
                price = 0.02 + (quarter * 0.01)
            else:  # Normal hours
                price = 0.12 + (quarter * 0.01)

            raw_today.append({
                "start": start,
                "end": end,
                "value": price,
            })

    state.attributes = {
        "raw_today": raw_today,
        "raw_tomorrow": [],  # Populated after 13:00 CET
        "unit": "EUR/kWh",
        "currency": "EUR",
    }

    return state


@pytest.fixture
def mock_battery_states(mock_hass):
    """Mock battery-related sensor states."""
    # Battery level sensor
    battery_level = MagicMock()
    battery_level.state = "75"
    battery_level.entity_id = "sensor.battery_level"
    battery_level.attributes = {"unit_of_measurement": "%"}

    # Battery capacity sensor
    battery_capacity = MagicMock()
    battery_capacity.state = "12.8"
    battery_capacity.entity_id = "sensor.battery_capacity"
    battery_capacity.attributes = {"unit_of_measurement": "kWh"}

    # Solar power sensor
    solar_power = MagicMock()
    solar_power.state = "2500"
    solar_power.entity_id = "sensor.solar_power"
    solar_power.attributes = {"unit_of_measurement": "W"}

    # Configure mock_hass states
    def get_state(entity_id):
        states_map = {
            "sensor.battery_level": battery_level,
            "sensor.battery_capacity": battery_capacity,
            "sensor.solar_power": solar_power,
        }
        return states_map.get(entity_id)

    mock_hass.states.get = Mock(side_effect=get_state)

    return {
        "battery_level": battery_level,
        "battery_capacity": battery_capacity,
        "solar_power": solar_power,
    }
