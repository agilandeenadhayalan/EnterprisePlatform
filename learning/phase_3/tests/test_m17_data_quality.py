"""Tests for Module 17: Data Quality Framework."""

import pytest

from learning.phase_3.src.m17_data_quality.profiling import (
    DataProfiler,
    DistributionAnalysis,
    CardinalityEstimation,
)
from learning.phase_3.src.m17_data_quality.rule_engine import (
    RuleEngine,
    QualityRule,
    RuleType,
    RuleStatus,
    Severity,
)
from learning.phase_3.src.m17_data_quality.anomaly_detection import (
    ZScoreDetector,
    IQRDetector,
    MovingAverageDetector,
)


# ── Profiling ──


class TestDataProfiler:
    def test_column_profile_basics(self):
        data = [
            {"id": 1, "val": 10.0},
            {"id": 2, "val": 20.0},
            {"id": 3, "val": 30.0},
        ]
        profiler = DataProfiler(data)
        profile = profiler.profile_column("val")
        assert profile.count == 3
        assert profile.null_count == 0
        assert profile.mean == 20.0
        assert profile.min_value == 10.0
        assert profile.max_value == 30.0

    def test_null_percentage(self):
        data = [
            {"val": 10.0},
            {"val": None},
            {"val": 30.0},
            {"val": None},
        ]
        profiler = DataProfiler(data)
        profile = profiler.profile_column("val")
        assert profile.null_pct == 50.0

    def test_distinct_count(self):
        data = [
            {"zone": "A"},
            {"zone": "B"},
            {"zone": "A"},
            {"zone": "C"},
        ]
        profiler = DataProfiler(data)
        profile = profiler.profile_column("zone")
        assert profile.distinct_count == 3

    def test_std_dev(self):
        data = [{"val": 10.0}, {"val": 20.0}, {"val": 30.0}]
        profiler = DataProfiler(data)
        profile = profiler.profile_column("val")
        assert profile.std_dev is not None
        assert profile.std_dev > 0

    def test_profile_all(self):
        data = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        profiler = DataProfiler(data)
        profiles = profiler.profile_all()
        assert len(profiles) == 2

    def test_empty_dataset_raises(self):
        with pytest.raises(ValueError, match="empty"):
            DataProfiler([])


class TestDistributionAnalysis:
    def test_percentiles(self):
        values = list(range(1, 101))
        pcts = DistributionAnalysis.percentiles(values)
        assert pcts["p50"] == pytest.approx(50.5, abs=0.5)
        assert pcts["p25"] < pcts["p50"] < pcts["p75"]

    def test_histogram_creates_buckets(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        hist = DistributionAnalysis.histogram(values, num_buckets=5)
        assert len(hist) == 5
        assert sum(hist.values()) == 10

    def test_skewness_symmetric(self):
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        skew = DistributionAnalysis.skewness(values)
        assert abs(skew) < 0.5  # Roughly symmetric


class TestCardinalityEstimation:
    def test_estimate_close_to_actual(self):
        hll = CardinalityEstimation(num_buckets=128)
        actual_values = [f"user_{i}" for i in range(1000)]
        for v in actual_values:
            hll.add(v)
        estimate = hll.estimate()
        # HyperLogLog should be within ~20% for 1000 elements
        assert 700 < estimate < 1500

    def test_exact_count(self):
        values = ["a", "b", "a", "c", "b"]
        assert CardinalityEstimation.exact_count(values) == 3


# ── Rule Engine ──


class TestRuleEngine:
    def test_completeness_pass(self):
        engine = RuleEngine()
        engine.add_rule(QualityRule(
            name="fare_complete", rule_type=RuleType.COMPLETENESS,
            column="fare", threshold=60.0,
        ))
        data = [{"fare": 10}, {"fare": 20}, {"fare": None}]
        results = engine.evaluate(data)
        assert results[0].status == RuleStatus.PASS
        assert results[0].metric_value == pytest.approx(66.67, abs=0.01)

    def test_completeness_fail(self):
        engine = RuleEngine()
        engine.add_rule(QualityRule(
            name="fare_complete", rule_type=RuleType.COMPLETENESS,
            column="fare", threshold=90.0,
        ))
        data = [{"fare": None}, {"fare": None}, {"fare": 10}]
        results = engine.evaluate(data)
        assert results[0].status == RuleStatus.FAIL

    def test_accuracy_in_range(self):
        engine = RuleEngine()
        engine.add_rule(QualityRule(
            name="fare_range", rule_type=RuleType.ACCURACY,
            column="fare", threshold=100.0,
            min_value=1.0, max_value=500.0,
        ))
        data = [{"fare": 25.0}, {"fare": 100.0}]
        results = engine.evaluate(data)
        assert results[0].status == RuleStatus.PASS

    def test_accuracy_out_of_range(self):
        engine = RuleEngine()
        engine.add_rule(QualityRule(
            name="fare_range", rule_type=RuleType.ACCURACY,
            column="fare", threshold=100.0,
            min_value=1.0, max_value=100.0,
        ))
        data = [{"fare": 25.0}, {"fare": 500.0}]
        results = engine.evaluate(data)
        assert results[0].status == RuleStatus.FAIL
        assert results[0].metric_value == 50.0

    def test_uniqueness_with_duplicates(self):
        engine = RuleEngine()
        engine.add_rule(QualityRule(
            name="id_unique", rule_type=RuleType.UNIQUENESS,
            column="id", threshold=100.0,
        ))
        data = [{"id": 1}, {"id": 2}, {"id": 1}]
        results = engine.evaluate(data)
        assert results[0].status == RuleStatus.FAIL
        assert results[0].records_failed == 1

    def test_format_regex(self):
        engine = RuleEngine()
        engine.add_rule(QualityRule(
            name="email_format", rule_type=RuleType.FORMAT,
            column="email", threshold=100.0,
            pattern=r"^[^@]+@[^@]+\.[^@]+$",
        ))
        data = [
            {"email": "alice@test.com"},
            {"email": "bad-email"},
        ]
        results = engine.evaluate(data)
        assert results[0].status == RuleStatus.FAIL
        assert results[0].metric_value == 50.0

    def test_freshness_with_data(self):
        engine = RuleEngine()
        engine.add_rule(QualityRule(
            name="data_fresh", rule_type=RuleType.FRESHNESS,
            column="updated_at", threshold=3600,
        ))
        data = [{"updated_at": "2024-01-01T10:00:00"}]
        results = engine.evaluate(data)
        assert results[0].status == RuleStatus.PASS


# ── Anomaly Detection ──


class TestZScoreDetector:
    def test_detects_outlier(self):
        values = [10, 11, 10, 12, 11, 10, 11, 100]  # 100 is an outlier
        detector = ZScoreDetector(threshold=2.0)
        report = detector.detect(values)
        assert report.has_anomalies
        assert any(a.value == 100 for a in report.anomalies)

    def test_no_anomalies_in_uniform_data(self):
        values = [10, 10, 10, 10, 10]
        detector = ZScoreDetector(threshold=3.0)
        report = detector.detect(values)
        assert not report.has_anomalies

    def test_threshold_validation(self):
        with pytest.raises(ValueError, match="positive"):
            ZScoreDetector(threshold=-1)


class TestIQRDetector:
    def test_detects_outlier(self):
        values = [10, 11, 12, 13, 14, 15, 100]
        detector = IQRDetector(multiplier=1.5)
        report = detector.detect(values)
        assert report.has_anomalies
        assert any(a.value == 100 for a in report.anomalies)

    def test_normal_data_no_anomalies(self):
        values = [10, 11, 12, 13, 14, 15, 16]
        detector = IQRDetector(multiplier=1.5)
        report = detector.detect(values)
        assert not report.has_anomalies


class TestMovingAverageDetector:
    def test_detects_spike(self):
        values = [10, 10, 10, 10, 10, 100, 10, 10]
        detector = MovingAverageDetector(window_size=4, threshold=2.0)
        report = detector.detect(values)
        assert report.has_anomalies
        assert any(a.value == 100 for a in report.anomalies)

    def test_window_size_validation(self):
        with pytest.raises(ValueError, match="at least 2"):
            MovingAverageDetector(window_size=1)
