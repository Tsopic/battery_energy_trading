"""Tests for dynamic price threshold calculation."""

from datetime import datetime

from custom_components.battery_energy_trading.dynamic_thresholds import (
    DynamicThresholdCalculator,
    DynamicThresholds,
    analyze_price_volatility,
)


class TestDynamicThresholdCalculator:
    """Tests for DynamicThresholdCalculator class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        calc = DynamicThresholdCalculator()
        assert calc.sell_percentile == 80.0
        assert calc.buy_percentile == 20.0
        assert calc.min_spread == 0.05

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        calc = DynamicThresholdCalculator(
            sell_percentile=90.0, buy_percentile=10.0, min_spread=0.10
        )
        assert calc.sell_percentile == 90.0
        assert calc.buy_percentile == 10.0
        assert calc.min_spread == 0.10

    def test_init_clamps_values(self):
        """Test that values are clamped to valid ranges."""
        calc = DynamicThresholdCalculator(
            sell_percentile=150.0, buy_percentile=-10.0, min_spread=-0.5
        )
        assert calc.sell_percentile == 100.0
        assert calc.buy_percentile == 0.0
        assert calc.min_spread == 0.0


class TestPercentileCalculation:
    """Tests for percentile calculation."""

    def test_calculate_percentile_empty_list(self):
        """Test percentile calculation with empty list."""
        calc = DynamicThresholdCalculator()
        result = calc.calculate_percentile([], 50)
        assert result == 0.0

    def test_calculate_percentile_single_value(self):
        """Test percentile calculation with single value."""
        calc = DynamicThresholdCalculator()
        result = calc.calculate_percentile([0.15], 50)
        assert result == 0.15

    def test_calculate_percentile_median(self):
        """Test 50th percentile (median) calculation."""
        calc = DynamicThresholdCalculator()
        prices = [0.10, 0.15, 0.20, 0.25, 0.30]
        result = calc.calculate_percentile(prices, 50)
        assert result == 0.20

    def test_calculate_percentile_p80(self):
        """Test 80th percentile calculation."""
        calc = DynamicThresholdCalculator()
        prices = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
        result = calc.calculate_percentile(prices, 80)
        # P80 of [0.05...0.50] should be around 0.41
        assert 0.40 <= result <= 0.42

    def test_calculate_percentile_p20(self):
        """Test 20th percentile calculation."""
        calc = DynamicThresholdCalculator()
        prices = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
        result = calc.calculate_percentile(prices, 20)
        # P20 of [0.05...0.50] should be around 0.14
        assert 0.13 <= result <= 0.15

    def test_calculate_percentile_extremes(self):
        """Test 0th and 100th percentile."""
        calc = DynamicThresholdCalculator()
        prices = [0.10, 0.20, 0.30]
        assert calc.calculate_percentile(prices, 0) == 0.10
        assert calc.calculate_percentile(prices, 100) == 0.30


class TestCalculateThresholds:
    """Tests for threshold calculation."""

    def test_calculate_thresholds_no_data(self):
        """Test calculation with no data."""
        calc = DynamicThresholdCalculator()
        result = calc.calculate_thresholds(None, None)

        assert result.sell_threshold is None
        assert result.buy_threshold is None
        assert result.spread is None
        assert result.trading_recommended is False
        assert result.price_count == 0

    def test_calculate_thresholds_empty_list(self):
        """Test calculation with empty list."""
        calc = DynamicThresholdCalculator()
        result = calc.calculate_thresholds([], None)

        assert result.sell_threshold is None
        assert result.price_count == 0

    def test_calculate_thresholds_today_only(self):
        """Test calculation with today's data only."""
        calc = DynamicThresholdCalculator()
        raw_today = [
            {"start": datetime(2024, 1, 26, h), "end": datetime(2024, 1, 26, h + 1), "value": v}
            for h, v in enumerate(
                [0.08, 0.10, 0.12, 0.15, 0.18, 0.25, 0.35, 0.42, 0.38, 0.30, 0.20, 0.15]
            )
        ]

        result = calc.calculate_thresholds(raw_today, None)

        assert result.sell_threshold is not None
        assert result.buy_threshold is not None
        assert result.spread is not None
        assert result.price_count == 12
        assert result.min_price == 0.08
        assert result.max_price == 0.42

    def test_calculate_thresholds_with_tomorrow(self):
        """Test calculation with today and tomorrow data."""
        calc = DynamicThresholdCalculator()
        raw_today = [{"value": v} for v in [0.10, 0.20, 0.30]]
        raw_tomorrow = [{"value": v} for v in [0.15, 0.25, 0.35]]

        result = calc.calculate_thresholds(raw_today, raw_tomorrow)

        assert result.price_count == 6
        assert result.min_price == 0.10
        assert result.max_price == 0.35

    def test_calculate_thresholds_high_spread_recommends_trading(self):
        """Test that high spread recommends trading."""
        calc = DynamicThresholdCalculator(min_spread=0.05)
        # Create price data with significant spread
        raw_today = [{"value": v} for v in [0.05, 0.10, 0.15, 0.20, 0.40, 0.50, 0.60]]

        result = calc.calculate_thresholds(raw_today, None)

        assert result.trading_recommended is True
        assert result.spread is not None
        assert result.spread >= 0.05

    def test_calculate_thresholds_low_spread_not_recommended(self):
        """Test that low spread does not recommend trading."""
        calc = DynamicThresholdCalculator(min_spread=0.20)
        # Create price data with minimal spread
        raw_today = [{"value": v} for v in [0.10, 0.11, 0.12, 0.13, 0.14, 0.15]]

        result = calc.calculate_thresholds(raw_today, None)

        assert result.trading_recommended is False


class TestGetEffectiveThresholds:
    """Tests for effective threshold selection."""

    def test_get_effective_static_when_disabled(self):
        """Test that static thresholds are used when dynamic is disabled."""
        calc = DynamicThresholdCalculator()
        raw_today = [{"value": v} for v in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]]

        sell, buy, is_dynamic = calc.get_effective_thresholds(
            raw_today=raw_today,
            raw_tomorrow=None,
            static_sell_price=0.30,
            static_buy_price=0.00,
            use_dynamic=False,
        )

        assert sell == 0.30
        assert buy == 0.00
        assert is_dynamic is False

    def test_get_effective_dynamic_when_enabled(self):
        """Test that dynamic thresholds are used when enabled and available."""
        calc = DynamicThresholdCalculator(min_spread=0.05)
        raw_today = [{"value": v} for v in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]]

        sell, buy, is_dynamic = calc.get_effective_thresholds(
            raw_today=raw_today,
            raw_tomorrow=None,
            static_sell_price=0.30,
            static_buy_price=0.00,
            use_dynamic=True,
        )

        assert is_dynamic is True
        assert sell != 0.30  # Should be different from static
        assert buy != 0.00  # Should be different from static

    def test_get_effective_fallback_on_no_data(self):
        """Test fallback to static when no data available."""
        calc = DynamicThresholdCalculator()

        sell, buy, is_dynamic = calc.get_effective_thresholds(
            raw_today=None,
            raw_tomorrow=None,
            static_sell_price=0.30,
            static_buy_price=0.00,
            use_dynamic=True,
        )

        assert sell == 0.30
        assert buy == 0.00
        assert is_dynamic is False

    def test_get_effective_fallback_on_low_spread(self):
        """Test fallback to static when spread is too low."""
        calc = DynamicThresholdCalculator(min_spread=0.50)  # High min spread
        raw_today = [{"value": v} for v in [0.10, 0.12, 0.14, 0.16, 0.18, 0.20]]

        sell, buy, is_dynamic = calc.get_effective_thresholds(
            raw_today=raw_today,
            raw_tomorrow=None,
            static_sell_price=0.30,
            static_buy_price=0.00,
            use_dynamic=True,
        )

        assert sell == 0.30
        assert buy == 0.00
        assert is_dynamic is False


class TestAnalyzePriceVolatility:
    """Tests for price volatility analysis."""

    def test_analyze_empty_list(self):
        """Test volatility analysis with empty list."""
        result = analyze_price_volatility([])
        assert result["std_dev"] == 0.0
        assert result["coefficient_of_variation"] == 0.0
        assert result["price_range"] == 0.0
        assert result["interquartile_range"] == 0.0

    def test_analyze_single_value(self):
        """Test volatility analysis with single value."""
        result = analyze_price_volatility([0.15])
        assert result["std_dev"] == 0.0
        assert result["price_range"] == 0.0

    def test_analyze_constant_prices(self):
        """Test volatility analysis with constant prices."""
        result = analyze_price_volatility([0.20, 0.20, 0.20, 0.20])
        assert result["std_dev"] == 0.0
        assert result["price_range"] == 0.0

    def test_analyze_variable_prices(self):
        """Test volatility analysis with variable prices."""
        prices = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
        result = analyze_price_volatility(prices)

        assert result["std_dev"] > 0
        assert result["coefficient_of_variation"] > 0
        assert (
            abs(result["price_range"] - 0.35) < 0.0001
        )  # 0.40 - 0.05, use tolerance for float comparison
        assert result["interquartile_range"] > 0


class TestDynamicThresholdsDataclass:
    """Tests for DynamicThresholds dataclass."""

    def test_dataclass_creation(self):
        """Test creating DynamicThresholds instance."""
        now = datetime.now()
        thresholds = DynamicThresholds(
            sell_threshold=0.35,
            buy_threshold=0.10,
            spread=0.25,
            trading_recommended=True,
            price_count=24,
            min_price=0.05,
            max_price=0.50,
            avg_price=0.25,
            calculated_at=now,
        )

        assert thresholds.sell_threshold == 0.35
        assert thresholds.buy_threshold == 0.10
        assert thresholds.spread == 0.25
        assert thresholds.trading_recommended is True
        assert thresholds.price_count == 24
        assert thresholds.calculated_at == now
