"""Tests for number platform."""
import pytest
from unittest.mock import Mock, MagicMock

from custom_components.battery_energy_trading.number import (
    async_setup_entry,
    BatteryTradingNumber,
)
from custom_components.battery_energy_trading.const import (
    DOMAIN,
    VERSION,
    DEFAULT_FORCED_DISCHARGE_HOURS,
    DEFAULT_MIN_EXPORT_PRICE,
    DEFAULT_MIN_FORCED_SELL_PRICE,
    DEFAULT_MAX_FORCE_CHARGE_PRICE,
    DEFAULT_DISCHARGE_RATE_KW,
    DEFAULT_CHARGE_RATE_KW,
)


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry):
    """Test number platform setup."""
    async_add_entities = Mock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify number entities were added
    assert async_add_entities.called
    numbers = async_add_entities.call_args[0][0]
    assert len(numbers) == 13  # All number entities
    for number in numbers:
        assert isinstance(number, BatteryTradingNumber)


@pytest.mark.asyncio
async def test_async_setup_entry_with_auto_detected_rates(
    mock_hass, mock_config_entry_sungrow
):
    """Test number platform setup with auto-detected rates."""
    async_add_entities = Mock()

    await async_setup_entry(mock_hass, mock_config_entry_sungrow, async_add_entities)

    numbers = async_add_entities.call_args[0][0]

    # Find discharge and charge rate entities
    discharge_rate = next(
        n for n in numbers if "discharge_rate" in n._number_type.lower()
    )
    charge_rate = next(n for n in numbers if "charge_rate" in n._number_type.lower())

    # Should use auto-detected rates from config entry options
    assert discharge_rate._attr_native_value == 10.0  # SH10RT
    assert charge_rate._attr_native_value == 10.0  # SH10RT


class TestBatteryTradingNumber:
    """Test BatteryTradingNumber entity."""

    @pytest.fixture
    def number_entity(self, mock_config_entry):
        """Create a number entity for testing."""
        return BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="test_number",
            name="Test Number",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            default=50.0,
            unit="%",
            icon="mdi:test",
        )

    def test_init(self, number_entity, mock_config_entry):
        """Test number entity initialization."""
        assert number_entity._entry == mock_config_entry
        assert number_entity._number_type == "test_number"
        assert number_entity._attr_name == "Test Number"
        assert (
            number_entity._attr_unique_id
            == f"{DOMAIN}_{mock_config_entry.entry_id}_test_number"
        )
        assert number_entity._attr_suggested_object_id == f"{DOMAIN}_test_number"
        assert number_entity._attr_native_min_value == 0.0
        assert number_entity._attr_native_max_value == 100.0
        assert number_entity._attr_native_step == 1.0
        assert number_entity._attr_native_value == 50.0
        assert number_entity._attr_native_unit_of_measurement == "%"
        assert number_entity._attr_icon == "mdi:test"
        assert number_entity._attr_has_entity_name is True

    def test_device_info(self, number_entity, mock_config_entry):
        """Test device info generation."""
        device_info = number_entity._attr_device_info
        assert device_info["identifiers"] == {(DOMAIN, mock_config_entry.entry_id)}
        assert device_info["name"] == "Battery Energy Trading"
        assert device_info["manufacturer"] == "Battery Energy Trading"
        assert device_info["model"] == "Energy Optimizer"
        assert device_info["sw_version"] == VERSION

    @pytest.mark.asyncio
    async def test_async_set_native_value_valid(self, number_entity):
        """Test setting a valid value."""
        number_entity.async_write_ha_state = Mock()

        await number_entity.async_set_native_value(75.0)

        assert number_entity._attr_native_value == 75.0
        number_entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_native_value_min(self, number_entity):
        """Test setting minimum value."""
        number_entity.async_write_ha_state = Mock()

        await number_entity.async_set_native_value(0.0)

        assert number_entity._attr_native_value == 0.0
        number_entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_native_value_max(self, number_entity):
        """Test setting maximum value."""
        number_entity.async_write_ha_state = Mock()

        await number_entity.async_set_native_value(100.0)

        assert number_entity._attr_native_value == 100.0
        number_entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_native_value_clamps_above_max(self, number_entity):
        """Test value is clamped when above maximum."""
        number_entity.async_write_ha_state = Mock()

        await number_entity.async_set_native_value(150.0)

        # Should be clamped to max (100.0)
        assert number_entity._attr_native_value == 100.0
        number_entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_native_value_clamps_below_min(self, number_entity):
        """Test value is clamped when below minimum."""
        number_entity.async_write_ha_state = Mock()

        await number_entity.async_set_native_value(-50.0)

        # Should be clamped to min (0.0)
        assert number_entity._attr_native_value == 0.0
        number_entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_set_native_value_rate_validation(self, mock_config_entry):
        """Test rate validation rejects non-positive values."""
        rate_entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="discharge_rate_kw",
            name="Discharge Rate",
            min_value=0.0,
            max_value=20.0,
            step=0.5,
            default=5.0,
            unit="kW",
            icon="mdi:battery",
        )
        rate_entity.async_write_ha_state = Mock()

        # Try to set rate to 0 (invalid)
        await rate_entity.async_set_native_value(0.0)

        # Value should not change (stays at default)
        assert rate_entity._attr_native_value == 5.0
        rate_entity.async_write_ha_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_set_native_value_rate_negative(self, mock_config_entry):
        """Test rate validation rejects negative values."""
        rate_entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="charge_rate_kw",
            name="Charge Rate",
            min_value=0.0,
            max_value=20.0,
            step=0.5,
            default=5.0,
            unit="kW",
            icon="mdi:battery",
        )
        rate_entity.async_write_ha_state = Mock()

        await rate_entity.async_set_native_value(-5.0)

        # Value should not change
        assert rate_entity._attr_native_value == 5.0
        rate_entity.async_write_ha_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_set_native_value_rate_positive(self, mock_config_entry):
        """Test rate validation accepts positive values."""
        rate_entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="discharge_rate_kw",
            name="Discharge Rate",
            min_value=1.0,
            max_value=20.0,
            step=0.5,
            default=5.0,
            unit="kW",
            icon="mdi:battery",
        )
        rate_entity.async_write_ha_state = Mock()

        await rate_entity.async_set_native_value(10.0)

        assert rate_entity._attr_native_value == 10.0
        rate_entity.async_write_ha_state.assert_called_once()


class TestSpecificNumberEntities:
    """Test specific number entity configurations."""

    def test_forced_discharge_hours(self, mock_config_entry):
        """Test forced discharge hours entity."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="forced_discharge_hours",
            name="Forced Discharge Hours",
            min_value=0,
            max_value=24,
            step=1,
            default=DEFAULT_FORCED_DISCHARGE_HOURS,
            unit="hours",
            icon="mdi:clock-outline",
        )

        assert entity._attr_native_min_value == 0
        assert entity._attr_native_max_value == 24
        assert entity._attr_native_step == 1
        assert entity._attr_native_value == DEFAULT_FORCED_DISCHARGE_HOURS
        assert entity._attr_native_unit_of_measurement == "hours"

    def test_min_export_price(self, mock_config_entry):
        """Test minimum export price entity."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="min_export_price",
            name="Minimum Export Price",
            min_value=-0.3,
            max_value=0.1,
            step=0.0001,
            default=DEFAULT_MIN_EXPORT_PRICE,
            unit="EUR",
            icon="mdi:currency-eur",
        )

        assert entity._attr_native_min_value == -0.3
        assert entity._attr_native_max_value == 0.1
        assert entity._attr_native_step == 0.0001
        assert entity._attr_native_value == DEFAULT_MIN_EXPORT_PRICE
        assert entity._attr_native_unit_of_measurement == "EUR"

    def test_min_forced_sell_price(self, mock_config_entry):
        """Test minimum forced sell price entity."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="min_forced_sell_price",
            name="Minimum Forced Sell Price",
            min_value=0,
            max_value=0.5,
            step=0.01,
            default=DEFAULT_MIN_FORCED_SELL_PRICE,
            unit="EUR",
            icon="mdi:currency-eur",
        )

        assert entity._attr_native_min_value == 0
        assert entity._attr_native_max_value == 0.5
        assert entity._attr_native_value == DEFAULT_MIN_FORCED_SELL_PRICE

    def test_max_force_charge_price(self, mock_config_entry):
        """Test maximum force charge price entity."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="max_force_charge_price",
            name="Maximum Force Charge Price",
            min_value=-0.5,
            max_value=0.20,
            step=0.005,
            default=DEFAULT_MAX_FORCE_CHARGE_PRICE,
            unit="EUR",
            icon="mdi:currency-eur",
        )

        assert entity._attr_native_min_value == -0.5
        assert entity._attr_native_max_value == 0.20
        assert entity._attr_native_value == DEFAULT_MAX_FORCE_CHARGE_PRICE

    def test_discharge_rate(self, mock_config_entry):
        """Test discharge rate entity."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="discharge_rate_kw",
            name="Battery Discharge Rate",
            min_value=1.0,
            max_value=20.0,
            step=0.5,
            default=DEFAULT_DISCHARGE_RATE_KW,
            unit="kW",
            icon="mdi:battery-arrow-up",
        )

        assert entity._attr_native_min_value == 1.0
        assert entity._attr_native_max_value == 20.0
        assert entity._attr_native_step == 0.5
        assert entity._attr_native_value == DEFAULT_DISCHARGE_RATE_KW
        assert entity._attr_native_unit_of_measurement == "kW"

    def test_charge_rate(self, mock_config_entry):
        """Test charge rate entity."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="charge_rate_kw",
            name="Battery Charge Rate",
            min_value=1.0,
            max_value=20.0,
            step=0.5,
            default=DEFAULT_CHARGE_RATE_KW,
            unit="kW",
            icon="mdi:battery-arrow-down",
        )

        assert entity._attr_native_min_value == 1.0
        assert entity._attr_native_max_value == 20.0
        assert entity._attr_native_value == DEFAULT_CHARGE_RATE_KW


class TestNumberEntityValidation:
    """Test validation logic in number entities."""

    @pytest.mark.asyncio
    async def test_percentage_entity_clamping(self, mock_config_entry):
        """Test percentage entities clamp correctly."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="battery_level",
            name="Battery Level",
            min_value=0,
            max_value=100,
            step=1,
            default=50,
            unit="%",
            icon="mdi:battery",
        )
        entity.async_write_ha_state = Mock()

        # Test above 100%
        await entity.async_set_native_value(150)
        assert entity._attr_native_value == 100

        # Test below 0%
        await entity.async_set_native_value(-25)
        assert entity._attr_native_value == 0

    @pytest.mark.asyncio
    async def test_price_entity_negative_values(self, mock_config_entry):
        """Test price entities handle negative values."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="min_export_price",
            name="Minimum Export Price",
            min_value=-0.3,
            max_value=0.1,
            step=0.001,
            default=0.0,
            unit="EUR",
            icon="mdi:currency-eur",
        )
        entity.async_write_ha_state = Mock()

        # Negative price should be allowed within range
        await entity.async_set_native_value(-0.1)
        assert entity._attr_native_value == -0.1

    @pytest.mark.asyncio
    async def test_hours_entity_zero_allowed(self, mock_config_entry):
        """Test hours entities allow zero (unlimited)."""
        entity = BatteryTradingNumber(
            entry=mock_config_entry,
            number_type="forced_discharge_hours",
            name="Forced Discharge Hours",
            min_value=0,
            max_value=24,
            step=1,
            default=2,
            unit="hours",
            icon="mdi:clock",
        )
        entity.async_write_ha_state = Mock()

        # Zero should be allowed (unlimited mode)
        await entity.async_set_native_value(0)
        assert entity._attr_native_value == 0
        entity.async_write_ha_state.assert_called_once()
