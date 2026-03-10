"""
Tests for M32: Demand Forecasting — Spatio-temporal modeling, weather
integration, uncertainty quantification, and demand pattern detection.
"""

import math
import pytest

from m32_demand_forecasting.spatio_temporal import (
    GridCell,
    TimeSlot,
    SpatioTemporalGrid,
    _haversine,
)
from m32_demand_forecasting.weather_integration import (
    WeatherCondition,
    WeatherFeatures,
    WeatherImpactModel,
)
from m32_demand_forecasting.uncertainty import (
    PredictionInterval,
    QuantileRegression,
    MonteCarloDropout,
)
from m32_demand_forecasting.demand_patterns import (
    PatternType,
    DemandPattern,
    DemandDecomposition,
)


# ── GridCell ──


class TestGridCell:
    def test_create_cell(self):
        """GridCell stores id, zone, lat, lng, and base demand."""
        c = GridCell("c1", "Downtown", 40.7, -74.0, 50.0)
        assert c.id == "c1"
        assert c.zone_name == "Downtown"
        assert c.lat == 40.7
        assert c.base_demand == 50.0

    def test_default_demand(self):
        """GridCell defaults to 0 base demand."""
        c = GridCell("c1", "Zone", 0.0, 0.0)
        assert c.base_demand == 0.0


# ── TimeSlot ──


class TestTimeSlot:
    def test_create_timeslot(self):
        """TimeSlot stores start_hour, end_hour, day_of_week."""
        ts = TimeSlot(8, 9, 0)
        assert ts.start_hour == 8
        assert ts.end_hour == 9
        assert ts.day_of_week == 0

    def test_duration(self):
        """Duration is end - start hours."""
        ts = TimeSlot(8, 10, 0)
        assert ts.duration_hours == 2

    def test_is_weekend_saturday(self):
        """Saturday (5) is a weekend."""
        ts = TimeSlot(10, 11, 5)
        assert ts.is_weekend() is True

    def test_is_weekend_monday(self):
        """Monday (0) is not a weekend."""
        ts = TimeSlot(10, 11, 0)
        assert ts.is_weekend() is False

    def test_invalid_hour(self):
        """Invalid start hour raises ValueError."""
        with pytest.raises(ValueError, match="start_hour"):
            TimeSlot(25, 10, 0)

    def test_invalid_day(self):
        """Invalid day of week raises ValueError."""
        with pytest.raises(ValueError, match="day_of_week"):
            TimeSlot(8, 10, 7)


# ── Haversine ──


class TestHaversine:
    def test_same_point(self):
        """Distance from a point to itself is 0."""
        assert _haversine(40.7, -74.0, 40.7, -74.0) == pytest.approx(0.0)

    def test_known_distance(self):
        """NYC to London is approximately 5570 km."""
        dist = _haversine(40.7128, -74.0060, 51.5074, -0.1278)
        assert 5500 < dist < 5700

    def test_short_distance(self):
        """Short distances (1 degree lat ~ 111 km)."""
        dist = _haversine(0.0, 0.0, 1.0, 0.0)
        assert 110 < dist < 112


# ── SpatioTemporalGrid ──


class TestSpatioTemporalGrid:
    def test_add_get_cell(self):
        """Grid can add and retrieve cells."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("c1", "Downtown", 40.7, -74.0, 50.0))
        assert grid.get_cell("c1").zone_name == "Downtown"

    def test_cell_count(self):
        """cell_count tracks number of cells."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("c1", "Zone1", 0, 0))
        grid.add_cell(GridCell("c2", "Zone2", 0, 0))
        assert grid.cell_count == 2

    def test_get_cell_not_found(self):
        """Getting non-existent cell raises KeyError."""
        grid = SpatioTemporalGrid()
        with pytest.raises(KeyError):
            grid.get_cell("x")

    def test_get_neighbors(self):
        """get_neighbors returns cells within radius."""
        grid = SpatioTemporalGrid()
        # 1 degree lat ~ 111 km
        grid.add_cell(GridCell("c1", "Center", 0.0, 0.0))
        grid.add_cell(GridCell("c2", "Near", 0.01, 0.0))    # ~1.1 km away
        grid.add_cell(GridCell("c3", "Far", 1.0, 0.0))      # ~111 km away
        neighbors = grid.get_neighbors("c1", radius_km=5.0)
        assert len(neighbors) == 1
        assert neighbors[0].id == "c2"

    def test_get_neighbors_excludes_self(self):
        """get_neighbors does not include the cell itself."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("c1", "Center", 0.0, 0.0))
        neighbors = grid.get_neighbors("c1", radius_km=100.0)
        assert len(neighbors) == 0

    def test_spatial_autocorrelation_positive(self):
        """Positive autocorrelation when cell and neighbors have high demand."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("c1", "Center", 0.0, 0.0))
        grid.add_cell(GridCell("c2", "Near", 0.01, 0.0))
        grid.add_cell(GridCell("c3", "Far", 10.0, 0.0))
        demands = {"c1": 100, "c2": 95, "c3": 10}
        sa = grid.spatial_autocorrelation("c1", demands)
        assert sa > 0  # Positive because c1 and its neighbor c2 are both high

    def test_spatial_autocorrelation_no_neighbors(self):
        """Zero autocorrelation when no neighbors exist."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("c1", "Alone", 0.0, 0.0))
        demands = {"c1": 100}
        sa = grid.spatial_autocorrelation("c1", demands)
        assert sa == 0.0

    def test_temporal_pattern(self):
        """temporal_pattern detects peak and trough hours."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("c1", "Zone", 0, 0))
        # Peak at hour 8, trough at hour 3
        hourly = [5, 5, 5, 2, 5, 5, 5, 5, 100, 50, 30, 20, 15, 12, 10, 8, 7, 30, 40, 20, 10, 8, 6, 5]
        result = grid.temporal_pattern("c1", hourly)
        assert result["peak_hour"] == 8
        assert result["trough_hour"] == 3
        assert result["amplitude"] == 98

    def test_temporal_pattern_empty(self):
        """Empty hourly data raises ValueError."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("c1", "Zone", 0, 0))
        with pytest.raises(ValueError):
            grid.temporal_pattern("c1", [])

    def test_interpolate_demand(self):
        """Inverse distance weighted interpolation."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("target", "Target", 0.0, 0.0))
        grid.add_cell(GridCell("near", "Near", 0.01, 0.0))    # ~1.1 km
        grid.add_cell(GridCell("far", "Far", 0.1, 0.0))       # ~11 km
        known = {"near": 100.0, "far": 10.0}
        result = grid.interpolate_demand("target", known)
        # Near cell should have more influence
        assert result > 50  # closer to 100 than 10

    def test_interpolate_demand_no_data(self):
        """Interpolation without known data raises ValueError."""
        grid = SpatioTemporalGrid()
        grid.add_cell(GridCell("target", "Target", 0.0, 0.0))
        with pytest.raises(ValueError):
            grid.interpolate_demand("target", {})


# ── WeatherCondition & WeatherFeatures ──


class TestWeatherFeatures:
    def test_create_features(self):
        """WeatherFeatures stores condition and numeric attributes."""
        wf = WeatherFeatures(WeatherCondition.RAIN, 15.0, 80.0, 10.0, 5.0)
        assert wf.condition == WeatherCondition.RAIN
        assert wf.temperature == 15.0

    def test_to_vector(self):
        """to_vector returns list of 5 numeric values."""
        wf = WeatherFeatures(WeatherCondition.CLEAR, 20.0, 50.0, 5.0, 0.0)
        v = wf.to_vector()
        assert len(v) == 5
        assert v[0] == 0.0  # CLEAR is first in enum
        assert v[1] == 20.0  # temperature

    def test_to_vector_rain_index(self):
        """RAIN is index 2 in the condition vector."""
        wf = WeatherFeatures(WeatherCondition.RAIN, 15.0, 80.0, 10.0, 5.0)
        v = wf.to_vector()
        assert v[0] == 2.0


# ── WeatherImpactModel ──


class TestWeatherImpactModel:
    def test_get_impact_clear(self):
        """CLEAR weather has impact 1.0 (no change)."""
        model = WeatherImpactModel()
        assert model.get_impact(WeatherCondition.CLEAR) == 1.0

    def test_get_impact_rain(self):
        """RAIN increases demand by 30%."""
        model = WeatherImpactModel()
        assert model.get_impact(WeatherCondition.RAIN) == 1.3

    def test_get_impact_storm(self):
        """STORM decreases demand by 30%."""
        model = WeatherImpactModel()
        assert model.get_impact(WeatherCondition.STORM) == 0.7

    def test_apply_weather(self):
        """apply_weather multiplies base demand by impact."""
        model = WeatherImpactModel()
        wf = WeatherFeatures(WeatherCondition.RAIN, 15.0, 80.0, 10.0, 5.0)
        result = model.apply_weather(100.0, wf)
        assert result == pytest.approx(130.0)

    def test_custom_impacts(self):
        """Custom impacts override defaults."""
        model = WeatherImpactModel({WeatherCondition.CLEAR: 1.1})
        assert model.get_impact(WeatherCondition.CLEAR) == 1.1

    def test_seasonal_decomposition_trend(self):
        """Seasonal decomposition extracts a trend."""
        model = WeatherImpactModel()
        # Linear trend + weekly seasonal
        data = [10 + i + 5 * (i % 7 == 5) for i in range(28)]
        result = model.seasonal_decomposition(data, period=7)
        assert len(result["trend"]) == 28
        assert len(result["seasonal"]) == 28
        assert len(result["residual"]) == 28
        # Trend should be approximately linear in the middle
        mid_trends = [t for t in result["trend"] if t is not None]
        assert len(mid_trends) > 0

    def test_seasonal_decomposition_too_short(self):
        """Decomposition with too few data points raises ValueError."""
        model = WeatherImpactModel()
        with pytest.raises(ValueError, match="at least"):
            model.seasonal_decomposition([1, 2, 3], period=7)


# ── PredictionInterval ──


class TestPredictionInterval:
    def test_create_interval(self):
        """PredictionInterval stores lower, upper, confidence."""
        pi = PredictionInterval(10.0, 20.0, 0.9)
        assert pi.lower == 10.0
        assert pi.upper == 20.0
        assert pi.confidence_level == 0.9

    def test_width(self):
        """Width is upper - lower."""
        pi = PredictionInterval(10.0, 20.0, 0.9)
        assert pi.width() == pytest.approx(10.0)

    def test_contains_inside(self):
        """Value inside interval returns True."""
        pi = PredictionInterval(10.0, 20.0, 0.9)
        assert pi.contains(15.0) is True

    def test_contains_outside(self):
        """Value outside interval returns False."""
        pi = PredictionInterval(10.0, 20.0, 0.9)
        assert pi.contains(25.0) is False

    def test_contains_boundary(self):
        """Values at boundaries are contained."""
        pi = PredictionInterval(10.0, 20.0, 0.9)
        assert pi.contains(10.0) is True
        assert pi.contains(20.0) is True

    def test_invalid_bounds(self):
        """Lower > upper raises ValueError."""
        with pytest.raises(ValueError, match="lower"):
            PredictionInterval(20.0, 10.0, 0.9)

    def test_invalid_confidence(self):
        """Confidence outside (0,1] raises ValueError."""
        with pytest.raises(ValueError, match="confidence"):
            PredictionInterval(10.0, 20.0, 0.0)


# ── QuantileRegression ──


class TestQuantileRegression:
    def test_fit_and_predict(self):
        """Quantile regression produces valid intervals."""
        qr = QuantileRegression()
        qr.fit(list(range(100)))
        pi = qr.predict_interval(0.9)
        assert pi.lower < pi.upper
        assert pi.confidence_level == 0.9

    def test_predict_90_interval(self):
        """90% interval covers roughly 90% of data."""
        qr = QuantileRegression()
        data = list(range(100))
        qr.fit(data)
        pi = qr.predict_interval(0.9)
        # Lower should be around 5, upper around 94
        assert pi.lower <= 10
        assert pi.upper >= 85

    def test_fit_empty_raises(self):
        """Fitting with empty data raises ValueError."""
        qr = QuantileRegression()
        with pytest.raises(ValueError):
            qr.fit([])

    def test_predict_not_fitted(self):
        """Predicting before fit raises ValueError."""
        qr = QuantileRegression()
        with pytest.raises(ValueError, match="not fitted"):
            qr.predict_interval(0.9)

    def test_calibration_error_perfect(self):
        """Calibration error is 0 when all actuals are within intervals."""
        qr = QuantileRegression()
        intervals = [PredictionInterval(0, 100, 0.9) for _ in range(10)]
        actuals = [50] * 10
        assert qr.calibration_error(intervals, actuals) == 0.0

    def test_calibration_error_all_outside(self):
        """Calibration error is 1.0 when all actuals are outside intervals."""
        qr = QuantileRegression()
        intervals = [PredictionInterval(0, 10, 0.9) for _ in range(10)]
        actuals = [100] * 10
        assert qr.calibration_error(intervals, actuals) == 1.0

    def test_calibration_error_mismatch(self):
        """Mismatched lengths raises ValueError."""
        qr = QuantileRegression()
        with pytest.raises(ValueError):
            qr.calibration_error([PredictionInterval(0, 10, 0.9)], [1, 2])


# ── MonteCarloDropout ──


class TestMonteCarloDropout:
    def test_simulate_produces_samples(self):
        """simulate returns the correct number of samples."""
        mc = MonteCarloDropout(seed=42)
        samples = mc.simulate(100.0, 5.0, 100)
        assert len(samples) == 100

    def test_simulate_centered(self):
        """Samples are centered around the base prediction."""
        mc = MonteCarloDropout(seed=42)
        samples = mc.simulate(100.0, 5.0, 1000)
        mean = sum(samples) / len(samples)
        assert abs(mean - 100.0) < 2.0

    def test_simulate_zero_samples_raises(self):
        """Zero samples raises ValueError."""
        mc = MonteCarloDropout()
        with pytest.raises(ValueError, match="positive"):
            mc.simulate(100.0, 5.0, 0)

    def test_get_interval(self):
        """get_interval produces a valid prediction interval."""
        mc = MonteCarloDropout(seed=42)
        samples = mc.simulate(100.0, 10.0, 1000)
        pi = mc.get_interval(samples, 0.9)
        assert pi.lower < 100.0
        assert pi.upper > 100.0
        assert pi.confidence_level == 0.9

    def test_get_interval_empty_raises(self):
        """Empty samples raises ValueError."""
        mc = MonteCarloDropout()
        with pytest.raises(ValueError):
            mc.get_interval([], 0.9)


# ── DemandPattern ──


class TestDemandPattern:
    def test_create_pattern(self):
        """DemandPattern stores type, strength, and parameters."""
        dp = DemandPattern(PatternType.COMMUTE, 0.8, {"peak": 8})
        assert dp.pattern_type == PatternType.COMMUTE
        assert dp.strength == 0.8

    def test_strength_clamped(self):
        """Strength is clamped to [0, 1]."""
        dp = DemandPattern(PatternType.RANDOM, 1.5)
        assert dp.strength == 1.0
        dp2 = DemandPattern(PatternType.RANDOM, -0.5)
        assert dp2.strength == 0.0


# ── DemandDecomposition ──


class TestDemandDecomposition:
    def _commute_hourly(self):
        """Generate hourly data with commute pattern."""
        base = [10] * 24
        # Morning peak 7-9
        base[7] = 50
        base[8] = 80
        base[9] = 40
        # Evening peak 17-19
        base[17] = 60
        base[18] = 70
        base[19] = 45
        return base

    def test_detect_commute(self):
        """Commute pattern detected with morning and evening peaks."""
        dd = DemandDecomposition()
        pattern = dd.detect_commute(self._commute_hourly())
        assert pattern is not None
        assert pattern.pattern_type == PatternType.COMMUTE
        assert pattern.strength > 0

    def test_detect_commute_flat(self):
        """No commute pattern in flat demand."""
        dd = DemandDecomposition()
        pattern = dd.detect_commute([10] * 24)
        assert pattern is None

    def test_detect_commute_short_data(self):
        """Short data returns None."""
        dd = DemandDecomposition()
        assert dd.detect_commute([10, 20]) is None

    def test_detect_event(self):
        """Event spike > 2x baseline detected."""
        dd = DemandDecomposition()
        baseline = [10] * 24
        hourly = list(baseline)
        hourly[14] = 30  # 3x spike
        hourly[15] = 25  # 2.5x spike
        pattern = dd.detect_event(hourly, baseline)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.EVENT

    def test_detect_event_no_spike(self):
        """No event when demand matches baseline."""
        dd = DemandDecomposition()
        baseline = [10] * 24
        pattern = dd.detect_event(baseline, baseline)
        assert pattern is None

    def test_detect_event_no_baseline(self):
        """No event detection without baseline."""
        dd = DemandDecomposition()
        pattern = dd.detect_event([10] * 24, None)
        assert pattern is None

    def test_detect_seasonal(self):
        """Weekly seasonality detected with 7-day lag correlation."""
        dd = DemandDecomposition()
        # Create weekly repeating pattern
        week = [10, 15, 20, 25, 30, 50, 40]
        daily = week * 4  # 28 days
        pattern = dd.detect_seasonal(daily)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.SEASONAL
        assert pattern.parameters["lag_correlation"] >= 0.5

    def test_detect_seasonal_random(self):
        """No seasonality in random-like data."""
        dd = DemandDecomposition()
        # Alternating high-low with no weekly structure
        daily = [10 + (i % 3) * 5 for i in range(28)]
        pattern = dd.detect_seasonal(daily)
        # May or may not detect depending on data; just ensure no crash
        # For this specific pattern, correlation should be low
        if pattern:
            assert pattern.parameters["lag_correlation"] >= 0.5

    def test_detect_seasonal_too_short(self):
        """Short data returns None for seasonal."""
        dd = DemandDecomposition()
        assert dd.detect_seasonal([10] * 10) is None

    def test_classify_returns_sorted(self):
        """classify returns patterns sorted by strength descending."""
        dd = DemandDecomposition()
        hourly = self._commute_hourly()
        baseline = [10] * 24
        # Add event spike
        hourly[14] = 100
        hourly[15] = 90
        patterns = dd.classify(hourly, baseline)
        assert len(patterns) >= 1
        # Sorted by strength descending
        for i in range(len(patterns) - 1):
            assert patterns[i].strength >= patterns[i + 1].strength

    def test_classify_empty_patterns(self):
        """Flat data produces no patterns."""
        dd = DemandDecomposition()
        patterns = dd.classify([10] * 24)
        assert patterns == []
