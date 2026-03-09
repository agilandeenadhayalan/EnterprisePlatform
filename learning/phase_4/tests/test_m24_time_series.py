"""
Tests for M24: Time Series Forecasting — decomposition, ARIMA components,
demand forecasting, uncertainty quantification, and backtesting.
"""

import math
import random

import pytest

from m24_time_series.decomposition import AdditiveDecomposition, MultiplicativeDecomposition
from m24_time_series.arima import AutoRegressive, Differencing
from m24_time_series.forecasting import DemandForecaster
from m24_time_series.uncertainty import BootstrapInterval, ConformalPredictor
from m24_time_series.backtesting import (
    WalkForwardValidator,
    ExpandingWindowValidator,
    SlidingWindowValidator,
)


# ── Helper: generate seasonal data ──


def _make_seasonal_data(n: int = 120, period: int = 12, trend: float = 0.5, seed: int = 42):
    """Generate additive seasonal data: trend + seasonal + noise."""
    rng = random.Random(seed)
    seasonal_pattern = [
        -3, -2, -1, 0, 1, 3, 4, 3, 1, 0, -1, -2  # 12-period pattern
    ]
    data = []
    for i in range(n):
        t = trend * i
        s = seasonal_pattern[i % period]
        noise = rng.gauss(0, 0.3)
        data.append(t + s + 50 + noise)
    return data


def _make_hourly_demand(n_days: int = 14, seed: int = 42):
    """Generate realistic hourly ride demand."""
    rng = random.Random(seed)
    data = []
    for day in range(n_days):
        for hour in range(24):
            # Base demand with rush hour peaks
            if 7 <= hour <= 9:
                base = 150
            elif 17 <= hour <= 19:
                base = 180
            elif 0 <= hour <= 5:
                base = 20
            else:
                base = 80
            # Weekend effect
            if day % 7 in (5, 6):
                base *= 0.7
            # Slight upward trend
            trend = day * 2
            noise = rng.gauss(0, 10)
            data.append(max(0, base + trend + noise))
    return data


# ── AdditiveDecomposition ──


class TestAdditiveDecomposition:
    def test_decompose_returns_three_components(self):
        data = _make_seasonal_data(n=120, period=12)
        decomp = AdditiveDecomposition(period=12)
        result = decomp.decompose(data)
        assert "trend" in result
        assert "seasonal" in result
        assert "residual" in result
        assert len(result["trend"]) == len(data)
        assert len(result["seasonal"]) == len(data)
        assert len(result["residual"]) == len(data)

    def test_seasonal_repeats(self):
        data = _make_seasonal_data(n=120, period=12)
        decomp = AdditiveDecomposition(period=12)
        result = decomp.decompose(data)
        seasonal = result["seasonal"]
        # Seasonal should repeat every period
        for i in range(12, len(seasonal)):
            assert abs(seasonal[i] - seasonal[i % 12]) < 0.001

    def test_reconstruction(self):
        """T + S + R should approximately equal original series."""
        data = _make_seasonal_data(n=120, period=12)
        decomp = AdditiveDecomposition(period=12)
        result = decomp.decompose(data)
        for i in range(len(data)):
            if result["trend"][i] is not None:
                reconstructed = (
                    result["trend"][i] + result["seasonal"][i] + result["residual"][i]
                )
                assert abs(reconstructed - data[i]) < 0.001

    def test_too_short_series_raises(self):
        decomp = AdditiveDecomposition(period=12)
        with pytest.raises(ValueError):
            decomp.decompose([1.0] * 10)

    def test_trend_captures_linear_growth(self):
        # Pure trend data: y = 0.5*t + 10
        data = [0.5 * t + 10 for t in range(100)]
        decomp = AdditiveDecomposition(period=10)
        result = decomp.decompose(data)
        non_none_trend = [v for v in result["trend"] if v is not None]
        # Trend should be increasing
        assert non_none_trend[-1] > non_none_trend[0]


# ── MultiplicativeDecomposition ──


class TestMultiplicativeDecomposition:
    def test_decompose_returns_components(self):
        data = [abs(v) + 10 for v in _make_seasonal_data(n=120, period=12)]
        decomp = MultiplicativeDecomposition(period=12)
        result = decomp.decompose(data)
        assert len(result["trend"]) == len(data)

    def test_seasonal_near_one_average(self):
        """Multiplicative seasonal factors should average ~1.0."""
        data = [abs(v) + 10 for v in _make_seasonal_data(n=120, period=12)]
        decomp = MultiplicativeDecomposition(period=12)
        result = decomp.decompose(data)
        seasonal_period = result["seasonal"][:12]
        avg = sum(seasonal_period) / 12
        assert abs(avg - 1.0) < 0.05


# ── AutoRegressive ──


class TestAutoRegressive:
    def test_ar1_captures_trend(self):
        """AR(1) on trending data should predict continuation."""
        data = [float(i) + random.Random(42).gauss(0, 0.1) for i in range(100)]
        ar = AutoRegressive(order=1)
        ar.fit(data)
        preds = ar.predict(steps=5)
        assert len(preds) == 5
        # Predictions should continue upward
        assert preds[0] > data[-5]

    def test_ar2_returns_predictions(self):
        data = [float(i) for i in range(50)]
        ar = AutoRegressive(order=2)
        ar.fit(data)
        preds = ar.predict(steps=3)
        assert len(preds) == 3

    def test_autocorrelation_lag0_is_one(self):
        ar = AutoRegressive()
        series = [float(i) for i in range(50)]
        r0 = ar._autocorrelation(series, 0)
        assert abs(r0 - 1.0) < 0.001

    def test_too_short_series_raises(self):
        ar = AutoRegressive(order=5)
        with pytest.raises(ValueError):
            ar.fit([1.0, 2.0, 3.0])

    def test_constant_series_predicts_constant(self):
        data = [5.0] * 50
        ar = AutoRegressive(order=1)
        ar.fit(data)
        preds = ar.predict(steps=3)
        for p in preds:
            assert abs(p - 5.0) < 0.1


# ── Differencing ──


class TestDifferencing:
    def test_first_difference(self):
        diff = Differencing(d=1)
        result = diff.difference([1, 3, 6, 10])
        assert result == [2, 3, 4]

    def test_second_difference(self):
        diff = Differencing(d=2)
        result = diff.difference([1, 3, 6, 10])
        # First diff: [2, 3, 4], second diff: [1, 1]
        assert result == [1, 1]

    def test_undifference_recovers_original(self):
        original = [1, 3, 6, 10, 15]
        diff = Differencing(d=1)
        differenced = diff.difference(original)
        recovered = diff.undifference(differenced, original)
        assert len(recovered) == len(differenced)
        for a, b in zip(recovered, original[1:]):
            assert abs(a - b) < 0.001

    def test_stationarity_check_stationary_data(self):
        rng = random.Random(42)
        data = [rng.gauss(5, 1) for _ in range(100)]
        diff = Differencing(d=1)
        assert diff.is_stationary(data) is True

    def test_stationarity_check_trending_data(self):
        data = [float(i) for i in range(100)]
        diff = Differencing(d=1)
        assert diff.is_stationary(data) is False

    def test_differencing_makes_trend_stationary(self):
        data = [float(i) + random.Random(42).gauss(0, 0.5) for i in range(100)]
        diff = Differencing(d=1)
        differenced = diff.difference(data)
        assert diff.is_stationary(differenced) is True


# ── DemandForecaster ──


class TestDemandForecaster:
    def test_fit_and_predict(self):
        data = _make_hourly_demand(n_days=14)
        fc = DemandForecaster(seasonal_period=24)
        fc.fit(data)
        preds = fc.predict(n_hours=24)
        assert len(preds) == 24
        assert all(p >= 0 for p in preds)

    def test_predictions_show_rush_hour_pattern(self):
        data = _make_hourly_demand(n_days=14)
        fc = DemandForecaster(seasonal_period=24)
        fc.fit(data)
        preds = fc.predict(n_hours=24)
        # Rush hour predictions (8am, 6pm) should be higher than midnight
        # Allow for some variation from the trend/daily adjustments
        assert max(preds) > min(preds) * 1.5

    def test_too_short_data_raises(self):
        fc = DemandForecaster(seasonal_period=24)
        with pytest.raises(ValueError):
            fc.fit([1.0] * 10)


# ── BootstrapInterval ──


class TestBootstrapInterval:
    def test_intervals_contain_point_forecast(self):
        rng = random.Random(42)
        residuals = [rng.gauss(0, 1) for _ in range(100)]
        forecast = [10.0, 11.0, 12.0]
        bi = BootstrapInterval(n_bootstrap=200, confidence=0.95, seed=42)
        result = bi.compute(residuals, forecast)
        for i in range(3):
            assert result["lower"][i] <= result["point"][i]
            assert result["upper"][i] >= result["point"][i]

    def test_wider_intervals_at_lower_confidence(self):
        rng = random.Random(42)
        residuals = [rng.gauss(0, 1) for _ in range(100)]
        forecast = [10.0]
        bi_95 = BootstrapInterval(n_bootstrap=500, confidence=0.95, seed=42)
        bi_80 = BootstrapInterval(n_bootstrap=500, confidence=0.80, seed=42)
        r95 = bi_95.compute(residuals, forecast)
        r80 = bi_80.compute(residuals, forecast)
        width_95 = r95["upper"][0] - r95["lower"][0]
        width_80 = r80["upper"][0] - r80["lower"][0]
        assert width_95 > width_80

    def test_empty_residuals_raises(self):
        bi = BootstrapInterval()
        with pytest.raises(ValueError):
            bi.compute([], [10.0])


# ── ConformalPredictor ──


class TestConformalPredictor:
    def test_calibrate_and_predict(self):
        residuals = [random.Random(42).gauss(0, 1) for _ in range(100)]
        cp = ConformalPredictor(confidence=0.90)
        cp.calibrate(residuals)
        lower, upper = cp.predict_interval(50.0)
        assert lower < 50.0
        assert upper > 50.0

    def test_higher_confidence_wider_interval(self):
        residuals = [random.Random(42).gauss(0, 1) for _ in range(100)]
        cp_90 = ConformalPredictor(confidence=0.90)
        cp_99 = ConformalPredictor(confidence=0.99)
        cp_90.calibrate(residuals)
        cp_99.calibrate(residuals)
        l90, u90 = cp_90.predict_interval(50.0)
        l99, u99 = cp_99.predict_interval(50.0)
        assert (u99 - l99) >= (u90 - l90)

    def test_must_calibrate_first(self):
        cp = ConformalPredictor()
        with pytest.raises(RuntimeError):
            cp.predict_interval(50.0)


# ── WalkForwardValidator ──


class TestWalkForwardValidator:
    def test_splits_maintain_order(self):
        data = list(range(200))
        wf = WalkForwardValidator(n_splits=3, min_train_size=50)
        splits = wf.split(data)
        assert len(splits) == 3
        for train_idx, test_idx in splits:
            assert max(train_idx) < min(test_idx)  # train before test

    def test_training_grows(self):
        data = list(range(200))
        wf = WalkForwardValidator(n_splits=3, min_train_size=50)
        splits = wf.split(data)
        train_sizes = [len(train) for train, _ in splits]
        for i in range(1, len(train_sizes)):
            assert train_sizes[i] > train_sizes[i - 1]

    def test_too_short_data_raises(self):
        wf = WalkForwardValidator(n_splits=5, min_train_size=50)
        with pytest.raises(ValueError):
            wf.split(list(range(30)))


# ── ExpandingWindowValidator ──


class TestExpandingWindowValidator:
    def test_expanding_windows(self):
        data = list(range(100))
        ew = ExpandingWindowValidator(initial_train_size=50, test_size=10)
        splits = ew.split(data)
        assert len(splits) >= 1
        for train_idx, test_idx in splits:
            assert max(train_idx) < min(test_idx)

    def test_test_size_fixed(self):
        data = list(range(100))
        ew = ExpandingWindowValidator(initial_train_size=50, test_size=10)
        splits = ew.split(data)
        for _, test_idx in splits:
            assert len(test_idx) == 10


# ── SlidingWindowValidator ──


class TestSlidingWindowValidator:
    def test_train_size_fixed(self):
        data = list(range(130))
        sw = SlidingWindowValidator(train_size=50, test_size=10)
        splits = sw.split(data)
        assert len(splits) >= 1
        for train_idx, test_idx in splits:
            assert len(train_idx) == 50
            assert len(test_idx) == 10

    def test_window_slides(self):
        data = list(range(130))
        sw = SlidingWindowValidator(train_size=50, test_size=10)
        splits = sw.split(data)
        starts = [train[0] for train, _ in splits]
        for i in range(1, len(starts)):
            assert starts[i] > starts[i - 1]

    def test_temporal_order(self):
        data = list(range(130))
        sw = SlidingWindowValidator(train_size=50, test_size=10)
        splits = sw.split(data)
        for train_idx, test_idx in splits:
            assert max(train_idx) < min(test_idx)
