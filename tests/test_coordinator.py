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


@pytest.mark.asyncio
async def test_coordinator_record_action(mock_hass, mock_nord_pool_state):
    """Test recording automation actions."""
    mock_hass.states.get = MagicMock(return_value=mock_nord_pool_state)

    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    # Record a discharge action
    coordinator.record_action(
        action="discharge",
        next_discharge_slot="2025-10-31T16:00:00",
        next_charge_slot="2025-11-01T02:00:00",
    )

    # Verify tracking fields are set
    assert coordinator._last_action == "discharge"
    assert coordinator._last_action_time is not None
    assert coordinator._automation_active is True
    assert coordinator._next_discharge_slot == "2025-10-31T16:00:00"
    assert coordinator._next_charge_slot == "2025-11-01T02:00:00"

    # Verify data includes tracking information
    data = await coordinator._async_update_data()
    assert data["last_action"] == "discharge"
    assert data["last_action_time"] is not None
    assert data["automation_active"] is True
    assert data["next_discharge_slot"] == "2025-10-31T16:00:00"
    assert data["next_charge_slot"] == "2025-11-01T02:00:00"


@pytest.mark.asyncio
async def test_coordinator_clear_action(mock_hass, mock_nord_pool_state):
    """Test clearing automation action status."""
    mock_hass.states.get = MagicMock(return_value=mock_nord_pool_state)

    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    # Record an action first
    coordinator.record_action("charge")
    assert coordinator._automation_active is True

    # Clear the action
    coordinator.clear_action()
    assert coordinator._automation_active is False

    # Verify data shows automation is not active
    data = await coordinator._async_update_data()
    assert data["automation_active"] is False


@pytest.mark.asyncio
async def test_coordinator_action_tracking_in_update_data(mock_hass, mock_nord_pool_state):
    """Test that action tracking data is included in update data by default."""
    mock_hass.states.get = MagicMock(return_value=mock_nord_pool_state)

    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    # Before recording any action
    data = await coordinator._async_update_data()
    assert data["last_action"] is None
    assert data["last_action_time"] is None
    assert data["automation_active"] is False
    assert data["next_discharge_slot"] is None
    assert data["next_charge_slot"] is None
