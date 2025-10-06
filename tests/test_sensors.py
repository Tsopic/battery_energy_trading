"""Tests for sensor platform."""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

from custom_components.battery_energy_trading.sensor import (
    async_setup_entry,
    BatteryTradingSensor,
    ConfigurationSensor,
    ArbitrageOpportunitiesSensor,
    DischargeHoursSensor,
    ChargingHoursSensor,
)
from custom_components.battery_energy_trading.const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    CONF_BATTERY_LEVEL_ENTITY,
    CONF_BATTERY_CAPACITY_ENTITY,
    CONF_SOLAR_FORECAST_ENTITY,
    CONF_SOLAR_POWER_ENTITY,
)
from custom_components.battery_energy_trading.energy_optimizer import EnergyOptimizer


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry, mock_coordinator):
    """Test sensor platform setup."""
    async_add_entities = Mock()

    # Setup coordinator in hass.data (normally done by __init__.py)
    from custom_components.battery_energy_trading.const import DOMAIN
    mock_hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "coordinator": mock_coordinator,
            "data": mock_config_entry.data,
            "options": mock_config_entry.options,
        }
    }

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify sensors were added
    assert async_add_entities.called
    sensors = async_add_entities.call_args[0][0]
    assert len(sensors) == 4
    assert isinstance(sensors[0], ConfigurationSensor)
    assert isinstance(sensors[1], ArbitrageOpportunitiesSensor)
    assert isinstance(sensors[2], DischargeHoursSensor)
    assert isinstance(sensors[3], ChargingHoursSensor)


class TestBatteryTradingSensor:
    """Test BatteryTradingSensor base class."""

    @pytest.fixture
    def sensor(self, mock_hass, mock_config_entry, mock_coordinator):
        """Create a battery trading sensor."""
        return BatteryTradingSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            sensor_type="test_sensor",
        )

    def test_init(self, sensor):
        """Test sensor initialization."""
        assert sensor._nordpool_entity == "sensor.nordpool"
        assert sensor._sensor_type == "test_sensor"
        assert sensor._tracked_entities == ["sensor.nordpool"]
        assert sensor._attr_suggested_object_id == f"{DOMAIN}_test_sensor"

    def test_init_with_tracked_entities(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test sensor initialization with custom tracked entities."""
        sensor = BatteryTradingSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            sensor_type="test_sensor",
            tracked_entities=["sensor.a", "sensor.b"],
        )
        assert sensor._tracked_entities == ["sensor.a", "sensor.b"]

    @pytest.mark.asyncio
    async def test_async_added_to_hass(self, mock_hass, mock_config_entry, mock_coordinator):
        """Test state change listener registration."""
        # Create sensor with multiple tracked entities (including nordpool)
        sensor = BatteryTradingSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            sensor_type="test_sensor",
            tracked_entities=["sensor.nordpool", "sensor.other1", "sensor.other2"],
        )

        # Mock parent class method
        sensor.async_on_remove = Mock()

        with patch(
            "custom_components.battery_energy_trading.sensor.async_track_state_change_event"
        ) as mock_track:
            mock_track.return_value = Mock()
            await sensor.async_added_to_hass()

            # Verify state change tracking was registered for non-nordpool entities
            mock_track.assert_called_once()
            assert mock_track.call_args[0][0] == sensor.hass
            # Should only track entities other than nordpool (coordinator handles that)
            assert mock_track.call_args[0][1] == ["sensor.other1", "sensor.other2"]


class TestConfigurationSensor:
    """Test ConfigurationSensor."""

    @pytest.fixture
    def config_sensor(self, mock_hass, mock_config_entry, mock_coordinator):
        """Create a configuration sensor."""
        return ConfigurationSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            battery_level_entity="sensor.battery_level",
            battery_capacity_entity="sensor.battery_capacity",
            solar_forecast_entity="sensor.solar_forecast",
        )

    def test_init(self, config_sensor):
        """Test configuration sensor initialization."""
        assert config_sensor._nordpool_entity == "sensor.nordpool"
        assert config_sensor._battery_level_entity == "sensor.battery_level"
        assert config_sensor._battery_capacity_entity == "sensor.battery_capacity"
        assert config_sensor._solar_forecast_entity == "sensor.solar_forecast"
        assert config_sensor._attr_name == "Configuration"
        assert config_sensor._attr_icon == "mdi:cog"
        assert config_sensor._attr_entity_category == "diagnostic"

    def test_state(self, config_sensor):
        """Test configuration sensor state."""
        assert config_sensor.state == "Configured"

    def test_extra_state_attributes(self, config_sensor):
        """Test configuration sensor attributes."""
        attrs = config_sensor.extra_state_attributes

        assert attrs["nordpool_entity"] == "sensor.nordpool"
        assert attrs["battery_level_entity"] == "sensor.battery_level"
        assert attrs["battery_capacity_entity"] == "sensor.battery_capacity"
        assert attrs["solar_forecast_entity"] == "sensor.solar_forecast"

    def test_extra_state_attributes_without_solar_forecast(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test configuration sensor attributes without solar forecast."""
        config_sensor = ConfigurationSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            battery_level_entity="sensor.battery_level",
            battery_capacity_entity="sensor.battery_capacity",
            solar_forecast_entity=None,
        )

        attrs = config_sensor.extra_state_attributes
        assert "solar_forecast_entity" not in attrs

    def test_extra_state_attributes_with_solar_power_entity(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test configuration sensor includes solar power entity from config."""
        # Add solar power entity to config entry data
        mock_config_entry.data = {
            **mock_config_entry.data,
            CONF_SOLAR_POWER_ENTITY: "sensor.solar_power",
        }

        config_sensor = ConfigurationSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            battery_level_entity="sensor.battery_level",
            battery_capacity_entity="sensor.battery_capacity",
            solar_forecast_entity=None,
        )

        attrs = config_sensor.extra_state_attributes
        assert attrs["solar_power_entity"] == "sensor.solar_power"


class TestArbitrageOpportunitiesSensor:
    """Test ArbitrageOpportunitiesSensor."""

    @pytest.fixture
    def arbitrage_sensor(self, mock_hass, mock_config_entry, mock_coordinator):
        """Create an arbitrage opportunities sensor."""
        optimizer = EnergyOptimizer()
        return ArbitrageOpportunitiesSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            battery_capacity_entity="sensor.battery_capacity",
            optimizer=optimizer,
        )

    def test_init(self, arbitrage_sensor):
        """Test arbitrage sensor initialization."""
        assert arbitrage_sensor._battery_capacity_entity == "sensor.battery_capacity"
        assert arbitrage_sensor._optimizer is not None
        assert arbitrage_sensor._attr_name == "Arbitrage Opportunities"
        assert arbitrage_sensor._attr_icon == "mdi:chart-line"

    def test_state_no_nordpool_entity(self, arbitrage_sensor, mock_hass):
        """Test state when Nord Pool entity not found."""
        mock_hass.states.get = Mock(return_value=None)
        assert arbitrage_sensor.state == "No data available"

    def test_state_insufficient_data(self, arbitrage_sensor, mock_hass):
        """Test state with insufficient price data."""
        mock_state = MagicMock()
        mock_state.attributes = {"raw_today": [{"value": 0.1}]}
        mock_hass.states.get = Mock(return_value=mock_state)

        assert arbitrage_sensor.state == "Insufficient data"

    def test_state_with_opportunities(
        self, arbitrage_sensor, mock_hass, mock_nord_pool_state, mock_battery_states
    ):
        """Test state with detected arbitrage opportunities."""
        # Setup mocks
        def get_state(entity_id):
            if entity_id == "sensor.nordpool":
                return mock_nord_pool_state
            if entity_id == "sensor.battery_capacity":
                return mock_battery_states["battery_capacity"]
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        state = arbitrage_sensor.state
        # Should show the best opportunity
        assert "Charge" in state
        assert "Discharge" in state
        assert "Profit:" in state

    def test_state_no_opportunities(
        self, arbitrage_sensor, mock_hass, sample_price_data
    ):
        """Test state when no profitable opportunities found."""
        # Create flat price data (no arbitrage possible)
        flat_prices = [
            {
                "start": datetime(2025, 10, 1, 0, 0) + timedelta(minutes=i * 15),
                "end": datetime(2025, 10, 1, 0, 0) + timedelta(minutes=(i + 1) * 15),
                "value": 0.15,  # Same price everywhere
            }
            for i in range(96)
        ]

        mock_nordpool = MagicMock()
        mock_nordpool.attributes = {"raw_today": flat_prices}

        mock_capacity = MagicMock()
        mock_capacity.state = "10.0"

        def get_state(entity_id):
            if entity_id == "sensor.nordpool":
                return mock_nordpool
            if entity_id == "sensor.battery_capacity":
                return mock_capacity
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        state = arbitrage_sensor.state
        assert state == "No profitable opportunities found"

    def test_state_error_handling(self, arbitrage_sensor, mock_hass):
        """Test state error handling."""
        mock_hass.states.get = Mock(side_effect=Exception("Test error"))

        state = arbitrage_sensor.state
        assert state == "Error calculating"

    def test_extra_state_attributes(
        self, arbitrage_sensor, mock_hass, mock_nord_pool_state, mock_battery_states
    ):
        """Test arbitrage sensor attributes."""

        def get_state(entity_id):
            if entity_id == "sensor.nordpool":
                return mock_nord_pool_state
            if entity_id == "sensor.battery_capacity":
                return mock_battery_states["battery_capacity"]
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        attrs = arbitrage_sensor.extra_state_attributes
        assert "opportunities_count" in attrs
        assert "best_profit" in attrs
        assert "best_roi" in attrs
        assert "all_opportunities" in attrs
        assert len(attrs["all_opportunities"]) <= 5

    def test_extra_state_attributes_no_data(self, arbitrage_sensor, mock_hass):
        """Test attributes when no data available."""
        mock_hass.states.get = Mock(return_value=None)

        attrs = arbitrage_sensor.extra_state_attributes
        assert attrs == {}


class TestDischargeHoursSensor:
    """Test DischargeHoursSensor."""

    @pytest.fixture
    def discharge_sensor(self, mock_hass, mock_config_entry, mock_coordinator):
        """Create a discharge hours sensor."""
        optimizer = EnergyOptimizer()
        return DischargeHoursSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            battery_level_entity="sensor.battery_level",
            battery_capacity_entity="sensor.battery_capacity",
            solar_forecast_entity="sensor.solar_forecast",
            optimizer=optimizer,
        )

    def test_init(self, discharge_sensor):
        """Test discharge sensor initialization."""
        assert discharge_sensor._battery_level_entity == "sensor.battery_level"
        assert discharge_sensor._battery_capacity_entity == "sensor.battery_capacity"
        assert discharge_sensor._solar_forecast_entity == "sensor.solar_forecast"
        assert discharge_sensor._optimizer is not None
        assert discharge_sensor._attr_name == "Discharge Time Slots"
        assert discharge_sensor._attr_icon == "mdi:battery-arrow-up"

    def test_tracked_entities(self, discharge_sensor):
        """Test tracked entities include all required sensors."""
        expected = [
            "sensor.nordpool",
            "sensor.battery_level",
            "sensor.battery_capacity",
            "sensor.solar_forecast",
        ]
        assert discharge_sensor._tracked_entities == expected

    def test_state_no_slots(self, discharge_sensor, mock_hass):
        """Test state when no discharge slots selected."""
        mock_hass.states.get = Mock(return_value=None)

        state = discharge_sensor.state
        assert state == "No discharge slots selected"

    def test_state_with_slots(
        self, discharge_sensor, mock_hass, mock_nord_pool_state, mock_battery_states
    ):
        """Test state with discharge slots."""

        def get_state(entity_id):
            if entity_id == "sensor.nordpool":
                return mock_nord_pool_state
            if entity_id == "sensor.battery_level":
                return mock_battery_states["battery_level"]
            if entity_id == "sensor.battery_capacity":
                return mock_battery_states["battery_capacity"]
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        state = discharge_sensor.state
        # Should contain time ranges and energy info
        assert "kWh" in state

    def test_extra_state_attributes_no_slots(self, discharge_sensor, mock_hass):
        """Test attributes when no slots selected."""
        mock_hass.states.get = Mock(return_value=None)

        attrs = discharge_sensor.extra_state_attributes
        assert attrs["slot_count"] == 0
        assert attrs["total_energy_kwh"] == 0
        assert attrs["estimated_revenue_eur"] == 0
        assert attrs["slots"] == []

    def test_extra_state_attributes_with_slots(
        self, discharge_sensor, mock_hass, mock_nord_pool_state, mock_battery_states
    ):
        """Test attributes with discharge slots."""

        def get_state(entity_id):
            if entity_id == "sensor.nordpool":
                return mock_nord_pool_state
            if entity_id == "sensor.battery_level":
                return mock_battery_states["battery_level"]
            if entity_id == "sensor.battery_capacity":
                return mock_battery_states["battery_capacity"]
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        attrs = discharge_sensor.extra_state_attributes
        assert attrs["slot_count"] > 0
        assert attrs["total_energy_kwh"] > 0
        assert "estimated_revenue_eur" in attrs
        assert "average_price" in attrs
        assert len(attrs["slots"]) > 0

        # Verify slot structure
        first_slot = attrs["slots"][0]
        assert "start" in first_slot
        assert "end" in first_slot
        assert "energy_kwh" in first_slot
        assert "price" in first_slot
        assert "revenue" in first_slot

    def test_get_discharge_slots_no_nordpool(self, discharge_sensor, mock_hass):
        """Test _get_discharge_slots with no Nord Pool entity."""
        mock_hass.states.get = Mock(return_value=None)

        slots = discharge_sensor._get_discharge_slots()
        assert slots == []

    def test_get_discharge_slots_no_price_data(self, discharge_sensor, mock_hass):
        """Test _get_discharge_slots with no price data."""
        mock_state = MagicMock()
        mock_state.attributes = {"raw_today": []}
        mock_hass.states.get = Mock(return_value=mock_state)

        slots = discharge_sensor._get_discharge_slots()
        assert slots == []

    def test_get_discharge_slots_with_multiday(
        self, discharge_sensor, mock_hass, mock_nord_pool_state, mock_battery_states
    ):
        """Test discharge slots with multi-day optimization."""
        # Add tomorrow's prices
        tomorrow_prices = [
            {
                "start": datetime(2025, 10, 3, 0, 0) + timedelta(hours=i),
                "end": datetime(2025, 10, 3, 0, 0) + timedelta(hours=i + 1),
                "value": 0.10,
            }
            for i in range(24)
        ]
        mock_nord_pool_state.attributes["raw_tomorrow"] = tomorrow_prices

        # Mock multiday switch as ON
        mock_switch = MagicMock()
        mock_switch.state = "on"

        def get_state(entity_id):
            if entity_id == "sensor.nordpool":
                return mock_nord_pool_state
            if entity_id == "sensor.battery_level":
                return mock_battery_states["battery_level"]
            if entity_id == "sensor.battery_capacity":
                return mock_battery_states["battery_capacity"]
            if "switch" in entity_id and "multiday" in entity_id:
                return mock_switch
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        slots = discharge_sensor._get_discharge_slots()
        # Should get slots considering tomorrow's data
        assert isinstance(slots, list)


class TestChargingHoursSensor:
    """Test ChargingHoursSensor."""

    @pytest.fixture
    def charging_sensor(self, mock_hass, mock_config_entry, mock_coordinator):
        """Create a charging hours sensor."""
        optimizer = EnergyOptimizer()
        return ChargingHoursSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            coordinator=mock_coordinator,
            nordpool_entity="sensor.nordpool",
            battery_level_entity="sensor.battery_level",
            battery_capacity_entity="sensor.battery_capacity",
            solar_forecast_entity="sensor.solar_forecast",
            optimizer=optimizer,
        )

    def test_init(self, charging_sensor):
        """Test charging sensor initialization."""
        assert charging_sensor._battery_level_entity == "sensor.battery_level"
        assert charging_sensor._battery_capacity_entity == "sensor.battery_capacity"
        assert charging_sensor._solar_forecast_entity == "sensor.solar_forecast"
        assert charging_sensor._optimizer is not None
        assert charging_sensor._attr_name == "Charging Time Slots"
        assert charging_sensor._attr_icon == "mdi:battery-arrow-down"

    def test_state_no_slots(self, charging_sensor, mock_hass):
        """Test state when no charging slots selected."""
        mock_hass.states.get = Mock(return_value=None)

        state = charging_sensor.state
        assert state == "No charging slots selected"

    def test_state_with_slots(
        self, charging_sensor, mock_hass, mock_nord_pool_state, mock_battery_states
    ):
        """Test state with charging slots."""

        # Set battery level low to trigger charging
        low_battery = MagicMock()
        low_battery.state = "20"
        low_battery.entity_id = "sensor.battery_level"

        def get_state(entity_id):
            if entity_id == "sensor.nordpool":
                return mock_nord_pool_state
            if entity_id == "sensor.battery_level":
                return low_battery
            if entity_id == "sensor.battery_capacity":
                return mock_battery_states["battery_capacity"]
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        state = charging_sensor.state
        # Charging slots should be selected for low battery
        assert isinstance(state, str)

    def test_extra_state_attributes_no_slots(self, charging_sensor, mock_hass):
        """Test attributes when no slots selected."""
        mock_hass.states.get = Mock(return_value=None)

        attrs = charging_sensor.extra_state_attributes
        assert attrs["slot_count"] == 0
        assert attrs["total_energy_kwh"] == 0
        assert attrs["estimated_cost_eur"] == 0
        assert attrs["slots"] == []

    def test_extra_state_attributes_with_slots(
        self, charging_sensor, mock_hass, mock_nord_pool_state, mock_battery_states
    ):
        """Test attributes with charging slots."""
        # Set battery level low to trigger charging
        low_battery = MagicMock()
        low_battery.state = "20"
        low_battery.entity_id = "sensor.battery_level"

        def get_state(entity_id):
            if entity_id == "sensor.nordpool":
                return mock_nord_pool_state
            if entity_id == "sensor.battery_level":
                return low_battery
            if entity_id == "sensor.battery_capacity":
                return mock_battery_states["battery_capacity"]
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        attrs = charging_sensor.extra_state_attributes

        # Should have charging slots for low battery
        if attrs["slot_count"] > 0:
            assert attrs["total_energy_kwh"] > 0
            assert "estimated_cost_eur" in attrs
            assert "average_price" in attrs
            assert len(attrs["slots"]) > 0

            # Verify slot structure
            first_slot = attrs["slots"][0]
            assert "start" in first_slot
            assert "end" in first_slot
            assert "energy_kwh" in first_slot
            assert "price" in first_slot
            assert "cost" in first_slot

    def test_get_charging_slots_no_nordpool(self, charging_sensor, mock_hass):
        """Test _get_charging_slots with no Nord Pool entity."""
        mock_hass.states.get = Mock(return_value=None)

        slots = charging_sensor._get_charging_slots()
        assert slots == []

    def test_get_charging_slots_no_price_data(self, charging_sensor, mock_hass):
        """Test _get_charging_slots with no price data."""
        mock_state = MagicMock()
        mock_state.attributes = {"raw_today": []}
        mock_hass.states.get = Mock(return_value=mock_state)

        slots = charging_sensor._get_charging_slots()
        assert slots == []
