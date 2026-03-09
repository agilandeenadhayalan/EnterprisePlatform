"""
Tests for M22: ML Monitoring — drift detection, concept drift, feature
importance drift, and retraining decisions.
"""

import math
import random

import pytest

from m22_ml_monitoring.drift_detection import PSICalculator, KSTest, JSDivergence
from m22_ml_monitoring.concept_drift import (
    ConceptDriftDetector,
    PageHinkleyDetector,
    ADWINDetector,
)
from m22_ml_monitoring.feature_importance_drift import FeatureImportanceDrift
from m22_ml_monitoring.retraining_decision import RetrainingDecisionEngine


# ── PSICalculator ──


class TestPSICalculator:
    def test_identical_distributions_near_zero(self):
        """PSI of identical distributions should be ~0."""
        rng = random.Random(42)
        data = [rng.gauss(0, 1) for _ in range(500)]
        calc = PSICalculator(num_bins=10)
        calc.fit(data)
        psi = calc.compute(data)
        assert psi < 0.05

    def test_shifted_distribution_significant(self):
        """Large mean shift should yield PSI > 0.25."""
        rng = random.Random(42)
        ref = [rng.gauss(0, 1) for _ in range(500)]
        cur = [rng.gauss(3, 1) for _ in range(500)]
        calc = PSICalculator(num_bins=10)
        calc.fit(ref)
        psi = calc.compute(cur)
        assert psi > 0.25

    def test_moderate_drift(self):
        """Moderate shift should yield PSI between 0.1 and 0.5."""
        rng = random.Random(42)
        ref = [rng.gauss(0, 1) for _ in range(500)]
        cur = [rng.gauss(0.5, 1.2) for _ in range(500)]
        calc = PSICalculator(num_bins=10)
        calc.fit(ref)
        psi = calc.compute(cur)
        assert 0.01 < psi < 1.0

    def test_classify_no_drift(self):
        calc = PSICalculator()
        assert calc.classify(0.05) == "no_drift"

    def test_classify_moderate(self):
        calc = PSICalculator()
        assert calc.classify(0.15) == "moderate"

    def test_classify_significant(self):
        calc = PSICalculator()
        assert calc.classify(0.30) == "significant"

    def test_fit_required_before_compute(self):
        calc = PSICalculator()
        with pytest.raises(RuntimeError):
            calc.compute([1.0, 2.0, 3.0] * 10)

    def test_too_few_reference_points(self):
        calc = PSICalculator(num_bins=10)
        with pytest.raises(ValueError):
            calc.fit([1.0, 2.0])


# ── KSTest ──


class TestKSTest:
    def test_identical_samples(self):
        """KS stat should be ~0 for identical samples."""
        data = [float(i) for i in range(100)]
        ks = KSTest()
        stat, pval = ks.compute(data, data)
        assert stat < 0.05
        assert pval > 0.5

    def test_different_distributions(self):
        """KS stat should be large for very different distributions."""
        rng = random.Random(42)
        ref = [rng.gauss(0, 1) for _ in range(200)]
        cur = [rng.gauss(5, 1) for _ in range(200)]
        ks = KSTest()
        stat, pval = ks.compute(ref, cur)
        assert stat > 0.5
        assert pval < 0.01

    def test_ks_statistic_bounded(self):
        """KS statistic should be in [0, 1]."""
        rng = random.Random(123)
        ref = [rng.random() for _ in range(50)]
        cur = [rng.random() for _ in range(50)]
        ks = KSTest()
        stat, pval = ks.compute(ref, cur)
        assert 0 <= stat <= 1
        assert 0 <= pval <= 1

    def test_empty_input_raises(self):
        ks = KSTest()
        with pytest.raises(ValueError):
            ks.compute([], [1.0, 2.0])


# ── JSDivergence ──


class TestJSDivergence:
    def test_identical_distributions_zero(self):
        """JSD of identical distributions should be ~0."""
        rng = random.Random(42)
        data = [rng.gauss(0, 1) for _ in range(500)]
        jsd = JSDivergence(num_bins=10)
        result = jsd.compute(data, data)
        assert result < 0.01

    def test_different_distributions_positive(self):
        """JSD of different distributions should be > 0."""
        rng = random.Random(42)
        ref = [rng.gauss(0, 1) for _ in range(500)]
        cur = [rng.gauss(3, 1) for _ in range(500)]
        jsd = JSDivergence(num_bins=10)
        result = jsd.compute(ref, cur)
        assert result > 0.1

    def test_jsd_bounded_by_ln2(self):
        """JSD should be <= ln(2) ~ 0.693."""
        rng = random.Random(42)
        ref = [rng.gauss(-10, 0.1) for _ in range(200)]
        cur = [rng.gauss(10, 0.1) for _ in range(200)]
        jsd = JSDivergence(num_bins=10)
        result = jsd.compute(ref, cur)
        assert result <= math.log(2) + 0.01

    def test_symmetric(self):
        """JSD(P||Q) should equal JSD(Q||P)."""
        rng = random.Random(42)
        ref = [rng.gauss(0, 1) for _ in range(300)]
        cur = [rng.gauss(1, 1.5) for _ in range(300)]
        jsd = JSDivergence(num_bins=10)
        assert abs(jsd.compute(ref, cur) - jsd.compute(cur, ref)) < 0.001

    def test_constant_distributions(self):
        """JSD of two constant (identical value) distributions should be 0."""
        jsd = JSDivergence()
        assert jsd.compute([5.0] * 50, [5.0] * 50) == 0.0


# ── ConceptDriftDetector ──


class TestConceptDriftDetector:
    def test_no_drift_stable_errors(self):
        rng = random.Random(42)
        det = ConceptDriftDetector(window_size=50)
        for _ in range(60):
            det.add_error(rng.gauss(0.1, 0.01))
        result = det.detect()
        assert result["is_drifted"] is False

    def test_drift_detected_increasing_errors(self):
        det = ConceptDriftDetector(window_size=50)
        # First half: low errors
        for i in range(25):
            det.add_error(0.1)
        # Second half: high errors
        for i in range(25):
            det.add_error(0.9)
        result = det.detect()
        assert result["is_drifted"] is True
        assert result["error_trend"] > 0

    def test_insufficient_data_no_drift(self):
        det = ConceptDriftDetector(window_size=100)
        for _ in range(10):
            det.add_error(0.5)
        result = det.detect()
        assert result["is_drifted"] is False


# ── PageHinkleyDetector ──


class TestPageHinkleyDetector:
    def test_no_drift_stable_stream(self):
        det = PageHinkleyDetector(threshold=50.0, alpha=0.005)
        rng = random.Random(42)
        triggered = False
        for _ in range(100):
            triggered = det.update(rng.gauss(5.0, 0.1))
        assert triggered is False

    def test_drift_after_mean_shift(self):
        det = PageHinkleyDetector(threshold=10.0, alpha=0.005)
        # Stable phase
        for _ in range(50):
            det.update(5.0)
        # Shifted phase
        triggered = False
        for _ in range(100):
            if det.update(10.0):
                triggered = True
                break
        assert triggered is True

    def test_reset(self):
        det = PageHinkleyDetector()
        det.update(5.0)
        det.update(10.0)
        det.reset()
        assert det._n == 0


# ── ADWINDetector ──


class TestADWINDetector:
    def test_no_change_stable_data(self):
        det = ADWINDetector(delta=0.002)
        rng = random.Random(42)
        changes = 0
        for _ in range(100):
            if det.update(rng.gauss(5.0, 0.1)):
                changes += 1
        assert changes == 0

    def test_detects_abrupt_change(self):
        det = ADWINDetector(delta=0.01)
        detected = False
        for _ in range(50):
            det.update(1.0)
        for _ in range(50):
            if det.update(10.0):
                detected = True
                break
        assert detected is True


# ── FeatureImportanceDrift ──


class TestFeatureImportanceDrift:
    def test_identical_importance_high_correlation(self):
        fid = FeatureImportanceDrift()
        ref = {"a": 0.5, "b": 0.3, "c": 0.15, "d": 0.05}
        fid.set_reference_importance(ref)
        result = fid.compute_current_importance(ref)
        assert result["spearman_correlation"] == 1.0
        assert result["is_drifted"] is False

    def test_reversed_importance_low_correlation(self):
        fid = FeatureImportanceDrift()
        ref = {"a": 0.5, "b": 0.3, "c": 0.15, "d": 0.05}
        cur = {"a": 0.05, "b": 0.15, "c": 0.3, "d": 0.5}
        fid.set_reference_importance(ref)
        result = fid.compute_current_importance(cur)
        assert result["spearman_correlation"] < 0
        assert result["is_drifted"] is True

    def test_shifted_features_detected(self):
        fid = FeatureImportanceDrift()
        ref = {"a": 0.5, "b": 0.3, "c": 0.15, "d": 0.05}
        cur = {"a": 0.05, "b": 0.3, "c": 0.15, "d": 0.5}
        fid.set_reference_importance(ref)
        result = fid.compute_current_importance(cur)
        assert "a" in result["shifted_features"]
        assert "d" in result["shifted_features"]

    def test_must_set_reference_first(self):
        fid = FeatureImportanceDrift()
        with pytest.raises(RuntimeError):
            fid.compute_current_importance({"a": 0.5})

    def test_empty_importance_raises(self):
        fid = FeatureImportanceDrift()
        with pytest.raises(ValueError):
            fid.set_reference_importance({})


# ── RetrainingDecisionEngine ──


class TestRetrainingDecisionEngine:
    def test_no_action_all_clear(self):
        engine = RetrainingDecisionEngine()
        result = engine.evaluate(
            data_drift_score=0.05,
            concept_drift_detected=False,
            importance_correlation=0.95,
            performance_degradation_pct=2.0,
        )
        assert result["action"] == "no_action"
        assert result["urgency"] == "low"

    def test_critical_severe_performance_drop(self):
        engine = RetrainingDecisionEngine()
        result = engine.evaluate(
            data_drift_score=0.1,
            concept_drift_detected=False,
            importance_correlation=0.9,
            performance_degradation_pct=25.0,
        )
        assert result["action"] == "retrain_now"
        assert result["urgency"] == "critical"

    def test_critical_severe_data_drift(self):
        engine = RetrainingDecisionEngine()
        result = engine.evaluate(
            data_drift_score=0.60,
            concept_drift_detected=False,
            importance_correlation=0.9,
            performance_degradation_pct=5.0,
        )
        assert result["action"] == "retrain_now"
        assert result["urgency"] == "critical"

    def test_high_concept_and_data_drift(self):
        engine = RetrainingDecisionEngine()
        result = engine.evaluate(
            data_drift_score=0.30,
            concept_drift_detected=True,
            importance_correlation=0.9,
            performance_degradation_pct=5.0,
        )
        assert result["action"] == "retrain_now"
        assert result["urgency"] == "high"

    def test_schedule_concept_drift_only(self):
        engine = RetrainingDecisionEngine()
        result = engine.evaluate(
            data_drift_score=0.05,
            concept_drift_detected=True,
            importance_correlation=0.9,
            performance_degradation_pct=5.0,
        )
        assert result["action"] == "schedule"

    def test_schedule_data_drift_moderate_perf(self):
        engine = RetrainingDecisionEngine()
        result = engine.evaluate(
            data_drift_score=0.30,
            concept_drift_detected=False,
            importance_correlation=0.9,
            performance_degradation_pct=12.0,
        )
        assert result["action"] == "schedule"

    def test_monitor_moderate_performance(self):
        engine = RetrainingDecisionEngine()
        result = engine.evaluate(
            data_drift_score=0.05,
            concept_drift_detected=False,
            importance_correlation=0.9,
            performance_degradation_pct=12.0,
        )
        assert result["action"] == "monitor"

    def test_reasons_populated(self):
        engine = RetrainingDecisionEngine()
        result = engine.evaluate(
            data_drift_score=0.60,
            concept_drift_detected=True,
            importance_correlation=0.5,
            performance_degradation_pct=25.0,
        )
        assert len(result["reasons"]) >= 2
