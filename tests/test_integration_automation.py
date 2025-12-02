"""Integration tests for automatic energy trading automation flow."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.battery_energy_trading import (
    async_setup,
    async_setup_entry,
    DOMAIN,
)
from custom_components.battery_energy_trading.coordinator import (
    BatteryEnergyTradingCoordinator,
)


@pytest.mark.asyncio
async def test_full_setup_and_service_flow(mock_hass, mock_config_entry):
    """Test complete setup flow: async_setup → async_setup_entry → service calls."""
    # Step 1: Setup integration (registers services)
    result = await async_setup(mock_hass, {})
    assert result is True
    assert DOMAIN in mock_hass.data

    # Verify all services are registered
    registered_services = [
        call[0][1] for call in mock_hass.services.async_register.call_args_list
    ]
    assert "sync_sungrow_parameters" in registered_services
    assert "generate_automation_scripts" in registered_services
    assert "force_refresh" in registered_services

    # Step 2: Setup config entry (creates coordinator and entities)
    with patch(
        "custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

        result = await async_setup_entry(mock_hass, mock_config_entry)
        assert result is True

        # Verify coordinator was created and stored
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
        assert "coordinator" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]

    # Step 3: Call force_refresh service
    force_refresh_handler = None
    for call in mock_hass.services.async_register.call_args_list:
        if call[0][1] == "force_refresh":
            force_refresh_handler = call[0][2]
            break

    assert force_refresh_handler is not None

    # Make async_request_refresh an AsyncMock
    mock_coordinator.async_request_refresh = AsyncMock()

    # Create service call mock
    from homeassistant.core import ServiceCall
    import inspect

    sig = inspect.signature(ServiceCall.__init__)
    if "hass" in sig.parameters:
        service_call = ServiceCall(
            hass=mock_hass,
            domain=DOMAIN,
            service="force_refresh",
            data={"config_entry_id": mock_config_entry.entry_id},
        )
    else:
        service_call = ServiceCall(
            domain=DOMAIN,
            service="force_refresh",
            data={"config_entry_id": mock_config_entry.entry_id},
        )

    # Call service
    await force_refresh_handler(service_call)

    # Verify coordinator refresh was called
    mock_coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_coordinator_action_tracking_flow(mock_hass, mock_nord_pool_state):
    """Test coordinator action tracking updates automation status sensor."""
    mock_hass.states.get = MagicMock(return_value=mock_nord_pool_state)

    # Create coordinator
    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    # Initial state - no action recorded
    data = await coordinator._async_update_data()
    assert data["last_action"] is None
    assert data["automation_active"] is False

    # Record discharge action
    coordinator.record_action(
        action="discharge",
        next_discharge_slot="2025-10-31T16:00:00",
        next_charge_slot="2025-11-01T02:00:00",
    )

    # Update data
    data = await coordinator._async_update_data()
    assert data["last_action"] == "discharge"
    assert data["automation_active"] is True
    assert data["next_discharge_slot"] == "2025-10-31T16:00:00"
    assert data["last_action_time"] is not None

    # Clear action
    coordinator.clear_action()

    # Update data again
    data = await coordinator._async_update_data()
    assert data["automation_active"] is False
    # last_action and timestamps persist after clear


@pytest.mark.asyncio
async def test_automation_status_sensor_responds_to_coordinator(
    mock_hass, mock_config_entry, mock_nord_pool_state
):
    """Test that automation status sensor reflects coordinator state changes."""
    from custom_components.battery_energy_trading.sensor import AutomationStatusSensor

    mock_hass.states.get = MagicMock(return_value=mock_nord_pool_state)

    # Create coordinator
    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    # Create automation status sensor
    sensor = AutomationStatusSensor(
        hass=mock_hass,
        entry=mock_config_entry,
        coordinator=coordinator,
        nordpool_entity="sensor.nordpool_test",
    )

    # Initial state - idle (but sensor needs data first)
    coordinator.data = await coordinator._async_update_data()
    assert sensor.native_value == "Idle"

    # Record discharge action
    coordinator.record_action("discharge")
    coordinator.data = await coordinator._async_update_data()

    # Sensor should show active discharge
    assert sensor.native_value == "Active - Discharging"
    attrs = sensor.extra_state_attributes
    assert attrs["last_action"] == "discharge"
    assert attrs["automation_active"] is True

    # Clear action
    coordinator.clear_action()
    coordinator.data = await coordinator._async_update_data()

    # Sensor should return to idle
    assert sensor.native_value == "Idle"


@pytest.mark.asyncio
@patch("custom_components.battery_energy_trading.SungrowHelper")
async def test_generate_automation_scripts_service(
    mock_sungrow_helper_class, mock_hass, mock_config_entry
):
    """Test generate_automation_scripts service creates automation YAML."""
    # Setup integration
    await async_setup(mock_hass, {})

    # Setup config entry with coordinator
    with patch(
        "custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

        await async_setup_entry(mock_hass, mock_config_entry)

    # Get generate_automation_scripts service handler
    generate_handler = None
    for call in mock_hass.services.async_register.call_args_list:
        if call[0][1] == "generate_automation_scripts":
            generate_handler = call[0][2]
            break

    assert generate_handler is not None

    # Create service call
    from homeassistant.core import ServiceCall
    import inspect

    sig = inspect.signature(ServiceCall.__init__)
    if "hass" in sig.parameters:
        service_call = ServiceCall(
            hass=mock_hass,
            domain=DOMAIN,
            service="generate_automation_scripts",
            data={"config_entry_id": mock_config_entry.entry_id},
        )
    else:
        service_call = ServiceCall(
            domain=DOMAIN,
            service="generate_automation_scripts",
            data={"config_entry_id": mock_config_entry.entry_id},
        )

    # Track event firing
    fired_events = []

    def capture_event(event_type, event_data=None):
        fired_events.append((event_type, event_data))

    # Mock bus if not already present
    if not hasattr(mock_hass, 'bus'):
        mock_hass.bus = MagicMock()
    mock_hass.bus.async_fire = capture_event

    # Call service
    await generate_handler(service_call)

    # Verify automation YAML was stored
    automation_key = f"{mock_config_entry.entry_id}_automations"
    assert automation_key in mock_hass.data[DOMAIN]

    automation_yaml = mock_hass.data[DOMAIN][automation_key]
    assert "automation:" in automation_yaml
    assert "Battery Trading: Smart Discharge Control" in automation_yaml
    assert "Battery Trading: Smart Charging Control" in automation_yaml

    # Verify event was fired
    assert len(fired_events) == 1
    event_type, event_data = fired_events[0]
    assert event_type == "battery_energy_trading_automation_generated"
    assert event_data["config_entry_id"] == mock_config_entry.entry_id
    assert "yaml" in event_data


@pytest.mark.asyncio
async def test_dashboard_service_buttons_integration(mock_hass, mock_config_entry):
    """Test that dashboard service buttons can call services successfully."""
    # Setup integration
    await async_setup(mock_hass, {})

    # Setup config entry
    with patch(
        "custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

        await async_setup_entry(mock_hass, mock_config_entry)

        # Simulate dashboard button clicks (service calls without config_entry_id)

        # Test 1: Generate Automation Scripts button
        generate_handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == "generate_automation_scripts":
                generate_handler = call[0][2]
                break

        from homeassistant.core import ServiceCall
        import inspect

        sig = inspect.signature(ServiceCall.__init__)
        if "hass" in sig.parameters:
            service_call = ServiceCall(
                hass=mock_hass,
                domain=DOMAIN,
                service="generate_automation_scripts",
                data={},  # No config_entry_id - should auto-detect
            )
        else:
            service_call = ServiceCall(
                domain=DOMAIN, service="generate_automation_scripts", data={}
            )

        # Mock async_entries to return our config entry
        mock_hass.config_entries.async_entries = MagicMock(
            return_value=[mock_config_entry]
        )
        mock_hass.config_entries.async_get_entry = MagicMock(
            return_value=mock_config_entry
        )

        # Mock bus.async_fire
        if not hasattr(mock_hass, 'bus'):
            mock_hass.bus = MagicMock()
        mock_hass.bus.async_fire = MagicMock()

        # Should not raise error
        await generate_handler(service_call)

        # Test 2: Force Refresh button
        force_refresh_handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == "force_refresh":
                force_refresh_handler = call[0][2]
                break

        if "hass" in sig.parameters:
            service_call = ServiceCall(
                hass=mock_hass, domain=DOMAIN, service="force_refresh", data={}
            )
        else:
            service_call = ServiceCall(domain=DOMAIN, service="force_refresh", data={})

        await force_refresh_handler(service_call)

        # Verify coordinator refresh was called
        mock_coordinator.async_request_refresh.assert_called()


@pytest.mark.asyncio
async def test_sensor_registration_includes_automation_status(
    mock_hass, mock_config_entry
):
    """Test that automation status sensor is registered with other sensors."""
    from custom_components.battery_energy_trading.sensor import async_setup_entry

    with patch(
        "custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator_class.return_value = mock_coordinator

        # Setup hass.data for entry
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": mock_coordinator,
                "data": mock_config_entry.data,
                "options": mock_config_entry.options,
            }
        }

        async_add_entities = MagicMock()
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        # Verify sensors were added
        assert async_add_entities.called
        sensors = async_add_entities.call_args[0][0]

        # Should have 6 sensors now (including automation_status and ai_status)
        assert len(sensors) == 6

        # Find automation status sensor
        from custom_components.battery_energy_trading.sensor import AutomationStatusSensor

        automation_status_sensor = None
        for sensor in sensors:
            if isinstance(sensor, AutomationStatusSensor):
                automation_status_sensor = sensor
                break

        assert automation_status_sensor is not None
        assert automation_status_sensor._attr_name == "Automation Status"


@pytest.mark.asyncio
async def test_end_to_end_automation_monitoring_flow(
    mock_hass, mock_config_entry, mock_nord_pool_state
):
    """Test complete flow: setup → record action → sensor updates → dashboard displays."""
    from custom_components.battery_energy_trading.sensor import AutomationStatusSensor

    mock_hass.states.get = MagicMock(return_value=mock_nord_pool_state)

    # Step 1: Create coordinator (simulates integration setup)
    coordinator = BatteryEnergyTradingCoordinator(mock_hass, "sensor.nordpool_test")

    # Step 2: Create automation status sensor (simulates sensor platform setup)
    sensor = AutomationStatusSensor(
        hass=mock_hass,
        entry=mock_config_entry,
        coordinator=coordinator,
        nordpool_entity="sensor.nordpool_test",
    )

    # Step 3: Initial state (automation idle)
    coordinator.data = await coordinator._async_update_data()
    assert sensor.native_value == "Idle"
    assert sensor.extra_state_attributes["automation_active"] is False

    # Step 4: User automation triggers discharge (simulates Sungrow automation running)
    coordinator.record_action(
        action="discharge",
        next_discharge_slot="2025-10-31T16:00:00",
        next_charge_slot=None,
    )

    # Step 5: Coordinator updates (happens every 60 seconds)
    coordinator.data = await coordinator._async_update_data()

    # Step 6: Sensor reflects new state
    assert sensor.native_value == "Active - Discharging"
    attrs = sensor.extra_state_attributes
    assert attrs["last_action"] == "discharge"
    assert attrs["last_action_time"] is not None
    assert attrs["automation_active"] is True
    assert attrs["next_scheduled_action"] == "2025-10-31T16:00:00"

    # Step 7: Discharge slot ends, automation returns to self-consumption
    coordinator.clear_action()
    coordinator.data = await coordinator._async_update_data()

    # Step 8: Sensor shows idle again
    assert sensor.native_value == "Idle"
    assert sensor.extra_state_attributes["automation_active"] is False

    # Step 9: Next slot triggers charging
    coordinator.record_action(
        action="charge",
        next_discharge_slot=None,
        next_charge_slot="2025-11-01T03:00:00",
    )
    coordinator.data = await coordinator._async_update_data()

    # Step 10: Sensor shows charging state
    assert sensor.native_value == "Active - Charging"
    assert sensor.extra_state_attributes["last_action"] == "charge"


@pytest.mark.asyncio
async def test_multiple_service_calls_in_sequence(mock_hass, mock_config_entry):
    """Test calling multiple services in sequence (as dashboard buttons would)."""
    # Setup
    await async_setup(mock_hass, {})

    with patch(
        "custom_components.battery_energy_trading.BatteryEnergyTradingCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        mock_hass.config_entries.async_entries = MagicMock(
            return_value=[mock_config_entry]
        )
        mock_hass.config_entries.async_get_entry = MagicMock(
            return_value=mock_config_entry
        )

        await async_setup_entry(mock_hass, mock_config_entry)

        # Get service handlers
        handlers = {}
        for call in mock_hass.services.async_register.call_args_list:
            service_name = call[0][1]
            handler = call[0][2]
            handlers[service_name] = handler

        from homeassistant.core import ServiceCall
        import inspect

        sig = inspect.signature(ServiceCall.__init__)

        # Sequence 1: Force refresh
        if "hass" in sig.parameters:
            call1 = ServiceCall(hass=mock_hass, domain=DOMAIN, service="force_refresh", data={})
        else:
            call1 = ServiceCall(domain=DOMAIN, service="force_refresh", data={})

        await handlers["force_refresh"](call1)
        assert mock_coordinator.async_request_refresh.call_count == 1

        # Sequence 2: Generate automations
        if "hass" in sig.parameters:
            call2 = ServiceCall(
                hass=mock_hass, domain=DOMAIN, service="generate_automation_scripts", data={}
            )
        else:
            call2 = ServiceCall(
                domain=DOMAIN, service="generate_automation_scripts", data={}
            )

        # Mock bus.async_fire if not already mocked
        if not hasattr(mock_hass, 'bus'):
            mock_hass.bus = MagicMock()
        mock_hass.bus.async_fire = MagicMock()

        await handlers["generate_automation_scripts"](call2)

        automation_key = f"{mock_config_entry.entry_id}_automations"
        assert automation_key in mock_hass.data[DOMAIN]

        # Sequence 3: Force refresh again (user clicked refresh after generating)
        if "hass" in sig.parameters:
            call3 = ServiceCall(hass=mock_hass, domain=DOMAIN, service="force_refresh", data={})
        else:
            call3 = ServiceCall(domain=DOMAIN, service="force_refresh", data={})

        await handlers["force_refresh"](call3)
        assert mock_coordinator.async_request_refresh.call_count == 2
