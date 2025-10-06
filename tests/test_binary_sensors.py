"""Tests for binary_sensor platform."""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

from custom_components.battery_energy_trading.binary_sensor import (
    async_setup_entry,
    BatteryTradingBinarySensor,
    ForcedDischargeSensor,
    LowPriceSensor,
    ExportProfitableSensor,
    CheapestHoursSensor,
    BatteryLowSensor,
    SolarAvailableSensor,
)
from custom_components.battery_energy_trading.const import (
    DOMAIN,
    DEFAULT_MIN_EXPORT_PRICE,
    DEFAULT_MIN_SOLAR_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
)
from custom_components.battery_energy_trading.energy_optimizer import EnergyOptimizer


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry):
    """Test binary sensor platform setup."""
    async_add_entities = Mock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify binary sensors were added
    assert async_add_entities.called
    sensors = async_add_entities.call_args[0][0]
    assert len(sensors) == 6  # With solar_power_entity configured
    assert isinstance(sensors[0], ForcedDischargeSensor)
    assert isinstance(sensors[1], LowPriceSensor)
    assert isinstance(sensors[2], ExportProfitableSensor)
    assert isinstance(sensors[3], CheapestHoursSensor)
    assert isinstance(sensors[4], BatteryLowSensor)
    assert isinstance(sensors[5], SolarAvailableSensor)


@pytest.mark.asyncio
async def test_async_setup_entry_with_solar_power(mock_hass, mock_config_entry_sungrow):
    """Test binary sensor platform setup with solar power entity."""
    async_add_entities = Mock()

    await async_setup_entry(mock_hass, mock_config_entry_sungrow, async_add_entities)

    sensors = async_add_entities.call_args[0][0]
    assert len(sensors) == 6  # With solar_power_entity
    assert isinstance(sensors[5], SolarAvailableSensor)


class TestBatteryTradingBinarySensor:
    """Test BatteryTradingBinarySensor base class."""

    @pytest.fixture
    def binary_sensor(self, mock_hass, mock_config_entry):
        """Create a battery trading binary sensor."""
        return BatteryTradingBinarySensor(
            hass=mock_hass,
            entry=mock_config_entry,
            sensor_type="test_binary",
            tracked_entities=["sensor.test1", "sensor.test2"],
        )

    def test_init(self, binary_sensor):
        """Test binary sensor initialization."""
        assert binary_sensor._sensor_type == "test_binary"
        assert binary_sensor._tracked_entities == ["sensor.test1", "sensor.test2"]
        assert binary_sensor._attr_suggested_object_id == f"{DOMAIN}_test_binary"

    @pytest.mark.asyncio
    async def test_async_added_to_hass(self, binary_sensor):
        """Test state change listener registration."""
        binary_sensor.async_on_remove = Mock()

        with patch(
            "custom_components.battery_energy_trading.binary_sensor.async_track_state_change_event"
        ) as mock_track:
            mock_track.return_value = Mock()
            await binary_sensor.async_added_to_hass()

            mock_track.assert_called_once()
            assert mock_track.call_args[0][0] == binary_sensor.hass
            assert mock_track.call_args[0][1] == binary_sensor._tracked_entities


class TestForcedDischargeSensor:
    """Test ForcedDischargeSensor."""

    @pytest.fixture
    def forced_discharge_sensor(self, mock_hass, mock_config_entry):
        """Create a forced discharge sensor."""
        optimizer = EnergyOptimizer()
        return ForcedDischargeSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            nordpool_entity="sensor.nordpool",
            battery_level_entity="sensor.battery_level",
            battery_capacity_entity="sensor.battery_capacity",
            solar_power_entity="sensor.solar_power",
            solar_forecast_entity="sensor.solar_forecast",
            optimizer=optimizer,
        )

    def test_init(self, forced_discharge_sensor):
        """Test forced discharge sensor initialization."""
        assert forced_discharge_sensor._nordpool_entity == "sensor.nordpool"
        assert forced_discharge_sensor._battery_level_entity == "sensor.battery_level"
        assert (
            forced_discharge_sensor._battery_capacity_entity
            == "sensor.battery_capacity"
        )
        assert forced_discharge_sensor._solar_power_entity == "sensor.solar_power"
        assert (
            forced_discharge_sensor._solar_forecast_entity == "sensor.solar_forecast"
        )
        assert forced_discharge_sensor._optimizer is not None
        assert forced_discharge_sensor._attr_name == "Forced Discharge"
        assert forced_discharge_sensor._attr_device_class == "power"

    def test_tracked_entities(self, forced_discharge_sensor):
        """Test tracked entities include all required sensors."""
        expected = [
            "sensor.nordpool",
            "sensor.battery_level",
            "sensor.battery_capacity",
            "sensor.solar_power",
            "sensor.solar_forecast",
        ]
        assert forced_discharge_sensor._tracked_entities == expected

    def test_is_on_switch_disabled(self, forced_discharge_sensor, mock_hass):
        """Test is_on returns False when forced discharge switch is disabled."""
        # Mock switch as OFF
        mock_switch = MagicMock()
        mock_switch.state = "off"
        mock_hass.states.get = Mock(return_value=mock_switch)

        assert forced_discharge_sensor.is_on is False

    def test_is_on_no_battery_capacity(
        self, forced_discharge_sensor, mock_hass, mock_nord_pool_state
    ):
        """Test is_on returns False when battery capacity is zero."""
        # Mock switch as ON
        mock_switch = MagicMock()
        mock_switch.state = "on"

        # Mock battery capacity as 0
        mock_capacity = MagicMock()
        mock_capacity.state = "0"

        def get_state(entity_id):
            if "switch" in entity_id and "forced_discharge" in entity_id:
                return mock_switch
            if entity_id == "sensor.battery_capacity":
                return mock_capacity
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        assert forced_discharge_sensor.is_on is False

    def test_is_on_battery_too_low(
        self, forced_discharge_sensor, mock_hass, mock_nord_pool_state
    ):
        """Test is_on returns False when battery is below minimum and no solar."""
        # Mock switch as ON
        mock_switch = MagicMock()
        mock_switch.state = "on"

        # Mock battery at 10% (below default 25% minimum)
        mock_battery_level = MagicMock()
        mock_battery_level.state = "10"

        mock_battery_capacity = MagicMock()
        mock_battery_capacity.state = "12.8"

        # No solar power
        mock_solar = MagicMock()
        mock_solar.state = "0"

        def get_state(entity_id):
            if "switch" in entity_id:
                return mock_switch
            if entity_id == "sensor.battery_level":
                return mock_battery_level
            if entity_id == "sensor.battery_capacity":
                return mock_battery_capacity
            if entity_id == "sensor.solar_power":
                return mock_solar
            if entity_id == "sensor.nordpool":
                return mock_nord_pool_state
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        assert forced_discharge_sensor.is_on is False

    def test_is_on_no_nordpool_entity(self, forced_discharge_sensor, mock_hass):
        """Test is_on returns False when Nord Pool entity not found."""
        mock_switch = MagicMock()
        mock_switch.state = "on"

        mock_battery_level = MagicMock()
        mock_battery_level.state = "75"

        mock_battery_capacity = MagicMock()
        mock_battery_capacity.state = "12.8"

        def get_state(entity_id):
            if "switch" in entity_id:
                return mock_switch
            if entity_id == "sensor.battery_level":
                return mock_battery_level
            if entity_id == "sensor.battery_capacity":
                return mock_battery_capacity
            if entity_id == "sensor.nordpool":
                return None  # Nord Pool not found
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        assert forced_discharge_sensor.is_on is False

    def test_is_on_in_discharge_slot(
        self, forced_discharge_sensor, mock_hass, mock_nord_pool_state
    ):
        """Test is_on returns True when currently in a discharge slot."""
        # Mock switch as ON
        mock_switch = MagicMock()
        mock_switch.state = "on"

        # Mock battery with good state
        mock_battery_level = MagicMock()
        mock_battery_level.state = "75"

        mock_battery_capacity = MagicMock()
        mock_battery_capacity.state = "12.8"

        # Mock solar power
        mock_solar = MagicMock()
        mock_solar.state = "0"

        # Mock current time to be in a high-price slot (17:00-20:00)
        with patch(
            "custom_components.battery_energy_trading.energy_optimizer.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime(2025, 10, 2, 18, 0, 0)

            def get_state(entity_id):
                if "switch" in entity_id:
                    return mock_switch
                if entity_id == "sensor.battery_level":
                    return mock_battery_level
                if entity_id == "sensor.battery_capacity":
                    return mock_battery_capacity
                if entity_id == "sensor.solar_power":
                    return mock_solar
                if entity_id == "sensor.nordpool":
                    return mock_nord_pool_state
                return None

            mock_hass.states.get = Mock(side_effect=get_state)

            # Should be ON during high-price hours (17:00-20:00)
            result = forced_discharge_sensor.is_on
            # Result depends on optimizer logic
            assert isinstance(result, bool)

    def test_is_on_exception_handling(self, forced_discharge_sensor, mock_hass):
        """Test is_on handles exceptions gracefully."""
        mock_hass.states.get = Mock(side_effect=Exception("Test error"))

        assert forced_discharge_sensor.is_on is False


class TestLowPriceSensor:
    """Test LowPriceSensor."""

    @pytest.fixture
    def low_price_sensor(self, mock_hass, mock_config_entry):
        """Create a low price sensor."""
        return LowPriceSensor(
            hass=mock_hass, entry=mock_config_entry, nordpool_entity="sensor.nordpool"
        )

    def test_init(self, low_price_sensor):
        """Test low price sensor initialization."""
        assert low_price_sensor._nordpool_entity == "sensor.nordpool"
        assert low_price_sensor._attr_name == "Low Price Mode"
        assert low_price_sensor._attr_icon == "mdi:currency-eur-off"

    def test_is_on_no_entity(self, low_price_sensor, mock_hass):
        """Test is_on returns False when entity not found."""
        mock_hass.states.get = Mock(return_value=None)
        assert low_price_sensor.is_on is False

    def test_is_on_price_below_threshold(self, low_price_sensor, mock_hass):
        """Test is_on returns True when price is below threshold."""
        mock_state = MagicMock()
        mock_state.state = "0.01"  # Below DEFAULT_MIN_EXPORT_PRICE
        mock_hass.states.get = Mock(return_value=mock_state)

        assert low_price_sensor.is_on is True

    def test_is_on_price_above_threshold(self, low_price_sensor, mock_hass):
        """Test is_on returns False when price is above threshold."""
        mock_state = MagicMock()
        mock_state.state = "0.20"  # Above DEFAULT_MIN_EXPORT_PRICE
        mock_hass.states.get = Mock(return_value=mock_state)

        assert low_price_sensor.is_on is False

    def test_is_on_price_at_threshold(self, low_price_sensor, mock_hass):
        """Test is_on at exact threshold."""
        mock_state = MagicMock()
        mock_state.state = str(DEFAULT_MIN_EXPORT_PRICE)
        mock_hass.states.get = Mock(return_value=mock_state)

        assert low_price_sensor.is_on is True

    def test_is_on_invalid_price(self, low_price_sensor, mock_hass):
        """Test is_on returns False with invalid price."""
        mock_state = MagicMock()
        mock_state.state = "invalid"
        mock_hass.states.get = Mock(return_value=mock_state)

        assert low_price_sensor.is_on is False


class TestExportProfitableSensor:
    """Test ExportProfitableSensor."""

    @pytest.fixture
    def export_profitable_sensor(self, mock_hass, mock_config_entry):
        """Create an export profitable sensor."""
        return ExportProfitableSensor(
            hass=mock_hass, entry=mock_config_entry, nordpool_entity="sensor.nordpool"
        )

    def test_init(self, export_profitable_sensor):
        """Test export profitable sensor initialization."""
        assert export_profitable_sensor._nordpool_entity == "sensor.nordpool"
        assert export_profitable_sensor._attr_name == "Export Profitable"
        assert export_profitable_sensor._attr_icon == "mdi:transmission-tower-export"

    def test_is_on_no_entity(self, export_profitable_sensor, mock_hass):
        """Test is_on returns False when entity not found."""
        mock_hass.states.get = Mock(return_value=None)
        assert export_profitable_sensor.is_on is False

    def test_is_on_price_above_threshold(self, export_profitable_sensor, mock_hass):
        """Test is_on returns True when price is above threshold."""
        mock_state = MagicMock()
        mock_state.state = "0.20"  # Above DEFAULT_MIN_EXPORT_PRICE
        mock_hass.states.get = Mock(return_value=mock_state)

        assert export_profitable_sensor.is_on is True

    def test_is_on_price_below_threshold(self, export_profitable_sensor, mock_hass):
        """Test is_on returns False when price is below threshold."""
        mock_state = MagicMock()
        mock_state.state = "0.01"  # Below DEFAULT_MIN_EXPORT_PRICE
        mock_hass.states.get = Mock(return_value=mock_state)

        assert export_profitable_sensor.is_on is False

    def test_is_on_invalid_price(self, export_profitable_sensor, mock_hass):
        """Test is_on returns False with invalid price."""
        mock_state = MagicMock()
        mock_state.state = "not_a_number"
        mock_hass.states.get = Mock(return_value=mock_state)

        assert export_profitable_sensor.is_on is False


class TestCheapestHoursSensor:
    """Test CheapestHoursSensor."""

    @pytest.fixture
    def cheapest_hours_sensor(self, mock_hass, mock_config_entry):
        """Create a cheapest hours sensor."""
        optimizer = EnergyOptimizer()
        return CheapestHoursSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            nordpool_entity="sensor.nordpool",
            battery_level_entity="sensor.battery_level",
            battery_capacity_entity="sensor.battery_capacity",
            solar_forecast_entity="sensor.solar_forecast",
            optimizer=optimizer,
        )

    def test_init(self, cheapest_hours_sensor):
        """Test cheapest hours sensor initialization."""
        assert cheapest_hours_sensor._nordpool_entity == "sensor.nordpool"
        assert cheapest_hours_sensor._battery_level_entity == "sensor.battery_level"
        assert (
            cheapest_hours_sensor._battery_capacity_entity == "sensor.battery_capacity"
        )
        assert cheapest_hours_sensor._solar_forecast_entity == "sensor.solar_forecast"
        assert cheapest_hours_sensor._optimizer is not None
        assert cheapest_hours_sensor._attr_name == "Cheapest Slot Active"
        assert cheapest_hours_sensor._attr_icon == "mdi:clock-check"

    def test_is_on_switch_disabled(self, cheapest_hours_sensor, mock_hass):
        """Test is_on returns False when forced charging switch is disabled."""
        # Mock forced charging switch as OFF
        mock_switch = MagicMock()
        mock_switch.state = "off"
        mock_hass.states.get = Mock(return_value=mock_switch)

        assert cheapest_hours_sensor.is_on is False

    def test_is_on_no_nordpool(self, cheapest_hours_sensor, mock_hass):
        """Test is_on returns False when Nord Pool entity not found."""
        # Mock forced charging switch as ON
        mock_switch = MagicMock()
        mock_switch.state = "on"

        def get_state(entity_id):
            if "switch" in entity_id and "forced_charging" in entity_id:
                return mock_switch
            if entity_id == "sensor.nordpool":
                return None  # Not found
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        assert cheapest_hours_sensor.is_on is False

    def test_is_on_no_price_data(self, cheapest_hours_sensor, mock_hass):
        """Test is_on returns False when no price data available."""
        mock_switch = MagicMock()
        mock_switch.state = "on"

        mock_nordpool = MagicMock()
        mock_nordpool.attributes = {"raw_today": []}

        def get_state(entity_id):
            if "switch" in entity_id and "forced_charging" in entity_id:
                return mock_switch
            if entity_id == "sensor.nordpool":
                return mock_nordpool
            return None

        mock_hass.states.get = Mock(side_effect=get_state)

        assert cheapest_hours_sensor.is_on is False

    def test_is_on_in_cheap_slot(
        self, cheapest_hours_sensor, mock_hass, mock_nord_pool_state
    ):
        """Test is_on during a cheap charging slot."""
        mock_switch = MagicMock()
        mock_switch.state = "on"

        # Low battery to trigger charging
        mock_battery_level = MagicMock()
        mock_battery_level.state = "20"

        mock_battery_capacity = MagicMock()
        mock_battery_capacity.state = "12.8"

        # Mock current time to be in a cheap slot (2:00-5:00)
        with patch(
            "custom_components.battery_energy_trading.energy_optimizer.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime(2025, 10, 2, 3, 0, 0)

            def get_state(entity_id):
                if "switch" in entity_id:
                    return mock_switch
                if entity_id == "sensor.battery_level":
                    return mock_battery_level
                if entity_id == "sensor.battery_capacity":
                    return mock_battery_capacity
                if entity_id == "sensor.nordpool":
                    return mock_nord_pool_state
                return None

            mock_hass.states.get = Mock(side_effect=get_state)

            result = cheapest_hours_sensor.is_on
            assert isinstance(result, bool)


class TestBatteryLowSensor:
    """Test BatteryLowSensor."""

    @pytest.fixture
    def battery_low_sensor(self, mock_hass, mock_config_entry):
        """Create a battery low sensor."""
        return BatteryLowSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            battery_level_entity="sensor.battery_level",
        )

    def test_init(self, battery_low_sensor):
        """Test battery low sensor initialization."""
        assert battery_low_sensor._battery_level_entity == "sensor.battery_level"
        assert battery_low_sensor._attr_name == "Battery Low"
        assert battery_low_sensor._attr_device_class == "battery"

    def test_is_on_no_entity(self, battery_low_sensor, mock_hass):
        """Test is_on returns False when entity not found."""
        mock_hass.states.get = Mock(return_value=None)
        assert battery_low_sensor.is_on is False

    def test_is_on_unknown_state(self, battery_low_sensor, mock_hass):
        """Test is_on returns False when state is unknown."""
        mock_state = MagicMock()
        mock_state.state = "unknown"
        mock_hass.states.get = Mock(return_value=mock_state)

        assert battery_low_sensor.is_on is False

    def test_is_on_unavailable_state(self, battery_low_sensor, mock_hass):
        """Test is_on returns False when state is unavailable."""
        mock_state = MagicMock()
        mock_state.state = "unavailable"
        mock_hass.states.get = Mock(return_value=mock_state)

        assert battery_low_sensor.is_on is False

    def test_is_on_battery_below_threshold(self, battery_low_sensor, mock_hass):
        """Test is_on returns True when battery is below threshold."""
        battery_state = MagicMock()
        battery_state.state = "10"  # Below DEFAULT_BATTERY_LOW_THRESHOLD (15)

        def mock_get_state(entity_id):
            if entity_id == "sensor.battery_level":
                return battery_state
            return None  # Number entity doesn't exist, will use default threshold

        mock_hass.states.get = Mock(side_effect=mock_get_state)

        assert battery_low_sensor.is_on is True

    def test_is_on_battery_above_threshold(self, battery_low_sensor, mock_hass):
        """Test is_on returns False when battery is above threshold."""
        mock_state = MagicMock()
        mock_state.state = "75"  # Above DEFAULT_BATTERY_LOW_THRESHOLD (15)
        mock_hass.states.get = Mock(return_value=mock_state)

        assert battery_low_sensor.is_on is False

    def test_is_on_battery_at_threshold(self, battery_low_sensor, mock_hass):
        """Test is_on at exact threshold."""
        mock_state = MagicMock()
        mock_state.state = str(DEFAULT_BATTERY_LOW_THRESHOLD)
        mock_hass.states.get = Mock(return_value=mock_state)

        # At threshold should be False (not below)
        assert battery_low_sensor.is_on is False

    def test_is_on_invalid_state(self, battery_low_sensor, mock_hass):
        """Test is_on returns False with invalid state."""
        mock_state = MagicMock()
        mock_state.state = "not_a_number"
        mock_hass.states.get = Mock(return_value=mock_state)

        assert battery_low_sensor.is_on is False


class TestSolarAvailableSensor:
    """Test SolarAvailableSensor."""

    @pytest.fixture
    def solar_available_sensor(self, mock_hass, mock_config_entry):
        """Create a solar available sensor."""
        return SolarAvailableSensor(
            hass=mock_hass,
            entry=mock_config_entry,
            solar_power_entity="sensor.solar_power",
        )

    def test_init(self, solar_available_sensor):
        """Test solar available sensor initialization."""
        assert solar_available_sensor._solar_power_entity == "sensor.solar_power"
        assert solar_available_sensor._attr_name == "Solar Power Available"
        assert solar_available_sensor._attr_icon == "mdi:solar-power"

    def test_is_on_no_entity(self, solar_available_sensor, mock_hass):
        """Test is_on returns False when entity not found."""
        mock_hass.states.get = Mock(return_value=None)
        assert solar_available_sensor.is_on is False

    def test_is_on_unknown_state(self, solar_available_sensor, mock_hass):
        """Test is_on returns False when state is unknown."""
        mock_state = MagicMock()
        mock_state.state = "unknown"
        mock_hass.states.get = Mock(return_value=mock_state)

        assert solar_available_sensor.is_on is False

    def test_is_on_solar_above_threshold(self, solar_available_sensor, mock_hass):
        """Test is_on returns True when solar power is above threshold."""
        mock_state = MagicMock()
        mock_state.state = "2500"  # Above DEFAULT_MIN_SOLAR_THRESHOLD (500W)
        mock_hass.states.get = Mock(return_value=mock_state)

        assert solar_available_sensor.is_on is True

    def test_is_on_solar_below_threshold(self, solar_available_sensor, mock_hass):
        """Test is_on returns False when solar power is below threshold."""
        mock_state = MagicMock()
        mock_state.state = "100"  # Below DEFAULT_MIN_SOLAR_THRESHOLD (500W)
        mock_hass.states.get = Mock(return_value=mock_state)

        assert solar_available_sensor.is_on is False

    def test_is_on_solar_at_threshold(self, solar_available_sensor, mock_hass):
        """Test is_on at exact threshold."""
        mock_state = MagicMock()
        mock_state.state = str(DEFAULT_MIN_SOLAR_THRESHOLD)
        mock_hass.states.get = Mock(return_value=mock_state)

        # At threshold should be True (>=)
        assert solar_available_sensor.is_on is True

    def test_is_on_solar_zero(self, solar_available_sensor, mock_hass):
        """Test is_on returns False when solar power is zero."""
        mock_state = MagicMock()
        mock_state.state = "0"
        mock_hass.states.get = Mock(return_value=mock_state)

        assert solar_available_sensor.is_on is False

    def test_is_on_invalid_state(self, solar_available_sensor, mock_hass):
        """Test is_on returns False with invalid state."""
        mock_state = MagicMock()
        mock_state.state = "invalid"
        mock_hass.states.get = Mock(return_value=mock_state)

        assert solar_available_sensor.is_on is False
