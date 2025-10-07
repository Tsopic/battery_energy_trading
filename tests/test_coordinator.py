"""Tests for coordinator.py."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.battery_energy_trading.coordinator import (
    BatteryEnergyTradingCoordinator,
)


@pytest.mark.asyncio
async def test_coordinator_init(mock_hass):
    """Test coordinator initialization."""
    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    assert coordinator._nordpool_entity == "sensor.nordpool_test"
    assert coordinator.name == "Battery Energy Trading"


@pytest.mark.asyncio
async def test_coordinator_update_success(mock_hass, mock_nord_pool_state):
    """Test successful data update."""
    mock_hass.states.get = MagicMock(return_value=mock_nord_pool_state)

    coordinator = BatteryEnergyTradingCoordinator(
        mock_hass, "sensor.nordpool_kwh_ee_eur_3_10_022"
    )

    data = await coordinator._async_update_data()

    assert data is not None
    assert "raw_today" in data
    assert "raw_tomorrow" in data
    assert "current_price" in data
    assert data["current_price"] == "0.15"
    assert len(data["raw_today"]) == 96  # 24 hours * 4 (15-min slots)


@pytest.mark.asyncio
async def test_coordinator_update_entity_not_found(mock_hass):
    """Test update when Nord Pool entity not found."""
    mock_hass.states.get = MagicMock(return_value=None)

    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nonexistent")

    with pytest.raises(UpdateFailed, match="not found"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_entity_unavailable(mock_hass):
    """Test update when Nord Pool entity is unavailable."""
    unavailable_state = MagicMock()
    unavailable_state.state = "unavailable"
    unavailable_state.entity_id = "sensor.nordpool_test"

    mock_hass.states.get = MagicMock(return_value=unavailable_state)

    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    with pytest.raises(UpdateFailed, match="unavailable"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_entity_unknown(mock_hass):
    """Test update when Nord Pool entity state is unknown."""
    unknown_state = MagicMock()
    unknown_state.state = "unknown"
    unknown_state.entity_id = "sensor.nordpool_test"

    mock_hass.states.get = MagicMock(return_value=unknown_state)

    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    with pytest.raises(UpdateFailed, match="unknown"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_missing_raw_today(mock_hass):
    """Test update when raw_today attribute is missing."""
    state_without_raw_today = MagicMock()
    state_without_raw_today.state = "0.15"
    state_without_raw_today.entity_id = "sensor.nordpool_test"
    state_without_raw_today.attributes = {}  # No raw_today

    mock_hass.states.get = MagicMock(return_value=state_without_raw_today)

    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    with pytest.raises(UpdateFailed, match="missing 'raw_today'"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_with_tomorrow_data(mock_hass, mock_nord_pool_state):
    """Test update with tomorrow's price data available."""
    # Add tomorrow's data
    tomorrow_data = [
        {
            "start": datetime(2025, 10, 3, hour, minute),
            "end": datetime(2025, 10, 3, hour, minute) + timedelta(minutes=15),
            "value": 0.20,
        }
        for hour in range(24)
        for minute in [0, 15, 30, 45]
    ]
    mock_nord_pool_state.attributes["raw_tomorrow"] = tomorrow_data

    mock_hass.states.get = MagicMock(return_value=mock_nord_pool_state)

    coordinator = BatteryEnergyTradingCoordinator(
        mock_hass, "sensor.nordpool_kwh_ee_eur_3_10_022"
    )

    data = await coordinator._async_update_data()

    assert data["raw_tomorrow"] is not None
    assert len(data["raw_tomorrow"]) == 96


@pytest.mark.asyncio
async def test_coordinator_update_exception_handling(mock_hass):
    """Test that exceptions are properly wrapped in UpdateFailed."""

    def raise_exception(*args, **kwargs):
        raise ValueError("Test error")

    mock_hass.states.get = MagicMock(side_effect=raise_exception)

    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    with pytest.raises(UpdateFailed, match="Error communicating with Nord Pool"):
        await coordinator._async_update_data()
