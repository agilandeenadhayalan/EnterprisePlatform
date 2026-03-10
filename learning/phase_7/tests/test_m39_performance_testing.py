"""
Tests for M39: Performance Testing — load patterns, latency analysis, queuing theory, capacity planning.
"""

import math
import pytest

from m39_performance_testing.load_patterns import (
    RampPattern,
    SpikePattern,
    SoakPattern,
    StressPattern,
    CompositePattern,
)
from m39_performance_testing.latency_analysis import (
    LatencySample,
    PercentileCalculator,
    HDRHistogram,
    ApdexScore,
    LatencyAnalyzer,
)
from m39_performance_testing.queuing_theory import (
    LittlesLaw,
    MM1Queue,
    MMcQueue,
    utilization_vs_latency,
    CapacityCalculator,
)
from m39_performance_testing.capacity_planning import (
    ResourceProfile,
    InstanceType,
    UtilizationAnalyzer,
    CapacityPlanner,
    ScalingRecommendation,
)


# ── RampPattern ──


class TestRampPattern:
    def test_start_value(self):
        """RPS at time 0 equals start_rps."""
        p = RampPattern(10, 100, 60)
        assert p.get_rps_at(0) == pytest.approx(10)

    def test_end_value(self):
        """RPS at end equals end_rps."""
        p = RampPattern(10, 100, 60)
        assert p.get_rps_at(60) == pytest.approx(100)

    def test_midpoint(self):
        """RPS at midpoint is average of start and end."""
        p = RampPattern(0, 100, 100)
        assert p.get_rps_at(50) == pytest.approx(50)

    def test_before_start_returns_zero(self):
        """Time before pattern start returns 0."""
        p = RampPattern(10, 100, 60)
        assert p.get_rps_at(-1) == 0.0

    def test_duration_property(self):
        """Duration property returns correct value."""
        p = RampPattern(10, 100, 60)
        assert p.duration == 60


# ── SpikePattern ──


class TestSpikePattern:
    def test_base_before_spike(self):
        """RPS before the spike is base_rps."""
        p = SpikePattern(base_rps=50, spike_rps=500, spike_at=30, spike_duration=10)
        assert p.get_rps_at(10) == pytest.approx(50)

    def test_spike_value(self):
        """RPS during spike window is spike_rps."""
        p = SpikePattern(base_rps=50, spike_rps=500, spike_at=30, spike_duration=10)
        assert p.get_rps_at(35) == pytest.approx(500)

    def test_base_after_spike(self):
        """RPS after the spike returns to base_rps."""
        p = SpikePattern(base_rps=50, spike_rps=500, spike_at=30, spike_duration=10)
        assert p.get_rps_at(45) == pytest.approx(50)

    def test_spike_boundary_start(self):
        """RPS at spike start boundary is spike_rps."""
        p = SpikePattern(base_rps=50, spike_rps=500, spike_at=30, spike_duration=10)
        assert p.get_rps_at(30) == pytest.approx(500)

    def test_spike_boundary_end(self):
        """RPS at spike end boundary returns to base_rps."""
        p = SpikePattern(base_rps=50, spike_rps=500, spike_at=30, spike_duration=10)
        assert p.get_rps_at(40) == pytest.approx(50)


# ── SoakPattern ──


class TestSoakPattern:
    def test_constant_rps(self):
        """RPS is constant throughout the soak duration."""
        p = SoakPattern(100, 3600)
        assert p.get_rps_at(0) == pytest.approx(100)
        assert p.get_rps_at(1800) == pytest.approx(100)
        assert p.get_rps_at(3600) == pytest.approx(100)

    def test_outside_returns_zero(self):
        """RPS outside duration returns 0."""
        p = SoakPattern(100, 60)
        assert p.get_rps_at(61) == 0.0

    def test_duration(self):
        """Duration is correct."""
        p = SoakPattern(100, 3600)
        assert p.duration == 3600


# ── StressPattern ──


class TestStressPattern:
    def test_start_rps(self):
        """RPS at time 0 is start_rps."""
        p = StressPattern(start_rps=100, step_rps=50, step_duration=30, max_rps=300)
        assert p.get_rps_at(0) == pytest.approx(100)

    def test_second_step(self):
        """RPS in second step is start + step_rps."""
        p = StressPattern(start_rps=100, step_rps=50, step_duration=30, max_rps=300)
        assert p.get_rps_at(30) == pytest.approx(150)

    def test_max_rps_capped(self):
        """RPS does not exceed max_rps."""
        p = StressPattern(start_rps=100, step_rps=50, step_duration=30, max_rps=200)
        # At step 2 (60s): 100 + 2*50 = 200 = max
        assert p.get_rps_at(60) <= 200

    def test_outside_returns_zero(self):
        """RPS after pattern ends returns 0."""
        p = StressPattern(start_rps=100, step_rps=50, step_duration=30, max_rps=200)
        assert p.get_rps_at(p.duration + 1) == 0.0


# ── CompositePattern ──


class TestCompositePattern:
    def test_first_pattern(self):
        """First pattern is active at time 0."""
        p1 = SoakPattern(50, 10)
        p2 = SoakPattern(100, 10)
        comp = CompositePattern([p1, p2])
        assert comp.get_rps_at(5) == pytest.approx(50)

    def test_second_pattern(self):
        """Second pattern is active after first ends."""
        p1 = SoakPattern(50, 10)
        p2 = SoakPattern(100, 10)
        comp = CompositePattern([p1, p2])
        assert comp.get_rps_at(15) == pytest.approx(100)

    def test_total_duration(self):
        """Total duration is sum of all pattern durations."""
        p1 = SoakPattern(50, 10)
        p2 = SoakPattern(100, 20)
        comp = CompositePattern([p1, p2])
        assert comp.duration == pytest.approx(30)

    def test_outside_returns_zero(self):
        """RPS outside total duration returns 0."""
        p1 = SoakPattern(50, 10)
        comp = CompositePattern([p1])
        assert comp.get_rps_at(15) == 0.0


# ── PercentileCalculator ──


class TestPercentileCalculator:
    def test_p50_median(self):
        """p50 returns the median."""
        pc = PercentileCalculator()
        pc.add_values([10, 20, 30, 40, 50])
        assert pc.p50() == pytest.approx(30, abs=1)

    def test_p95(self):
        """p95 returns high percentile."""
        pc = PercentileCalculator()
        pc.add_values(list(range(1, 101)))  # 1..100
        assert pc.p95() == pytest.approx(95, abs=2)

    def test_p99(self):
        """p99 returns very high percentile."""
        pc = PercentileCalculator()
        pc.add_values(list(range(1, 101)))
        assert pc.p99() == pytest.approx(99, abs=2)

    def test_single_value(self):
        """Single value is all percentiles."""
        pc = PercentileCalculator()
        pc.add_values([42.0])
        assert pc.p50() == pytest.approx(42)
        assert pc.p99() == pytest.approx(42)

    def test_from_samples(self):
        """Can add LatencySample objects."""
        pc = PercentileCalculator()
        samples = [LatencySample(0, d) for d in [10, 20, 30, 40, 50]]
        pc.add_samples(samples)
        assert pc.p50() == pytest.approx(30, abs=1)

    def test_empty_returns_zero(self):
        """Empty calculator returns 0."""
        pc = PercentileCalculator()
        assert pc.p50() == 0.0


# ── HDRHistogram ──


class TestHDRHistogram:
    def test_record_and_mean(self):
        """Mean reflects recorded values."""
        h = HDRHistogram()
        for v in [10, 20, 30, 40, 50]:
            h.record(v)
        assert h.mean() == pytest.approx(30)

    def test_min_max(self):
        """Min and max track extremes."""
        h = HDRHistogram()
        for v in [5, 10, 100]:
            h.record(v)
        assert h.min() == 5
        assert h.max() == 100

    def test_percentile(self):
        """Percentile returns expected value."""
        h = HDRHistogram()
        for v in range(1, 101):
            h.record(v)
        assert h.percentile(50) == pytest.approx(50, abs=2)

    def test_stddev(self):
        """Stddev is positive for varied data."""
        h = HDRHistogram()
        for v in [10, 20, 30, 40, 50]:
            h.record(v)
        assert h.stddev() > 0

    def test_distribution_buckets(self):
        """Distribution returns bucket counts."""
        h = HDRHistogram()
        h.record(0.5)   # <1ms
        h.record(5.0)   # 1-10ms
        h.record(50.0)  # 10-100ms
        dist = h.get_distribution()
        assert dist["<1ms"] == 1
        assert dist["1-10ms"] == 1
        assert dist["10-100ms"] == 1


# ── ApdexScore ──


class TestApdexScore:
    def test_all_satisfied(self):
        """All requests below threshold gives Apdex 1.0."""
        apdex = ApdexScore(satisfied_threshold_ms=200)
        samples = [LatencySample(0, 100) for _ in range(10)]
        assert apdex.calculate(samples) == pytest.approx(1.0)

    def test_all_frustrated(self):
        """All requests above 4T gives Apdex 0.0."""
        apdex = ApdexScore(satisfied_threshold_ms=100)
        samples = [LatencySample(0, 500) for _ in range(10)]
        assert apdex.calculate(samples) == pytest.approx(0.0)

    def test_mixed_apdex(self):
        """Mixed satisfied/tolerating/frustrated produces expected score."""
        apdex = ApdexScore(satisfied_threshold_ms=100)
        samples = [
            LatencySample(0, 50),   # satisfied
            LatencySample(0, 200),  # tolerating (< 400)
            LatencySample(0, 500),  # frustrated (>= 400)
        ]
        # (1 + 0.5) / 3 = 0.5
        assert apdex.calculate(samples) == pytest.approx(0.5)

    def test_classify_satisfied(self):
        """Classifies below threshold as satisfied."""
        apdex = ApdexScore(satisfied_threshold_ms=200)
        assert apdex.classify(100) == "satisfied"

    def test_classify_frustrated(self):
        """Classifies above 4T as frustrated."""
        apdex = ApdexScore(satisfied_threshold_ms=100)
        assert apdex.classify(500) == "frustrated"


# ── LatencyAnalyzer ──


class TestLatencyAnalyzer:
    def test_analyze_basic(self):
        """Analyze returns expected keys."""
        la = LatencyAnalyzer()
        samples = [LatencySample(0, d) for d in [10, 20, 30, 40, 50]]
        result = la.analyze(samples)
        assert "p50" in result
        assert "p95" in result
        assert "mean" in result

    def test_empty_samples(self):
        """Empty sample list returns count 0."""
        la = LatencyAnalyzer()
        result = la.analyze([])
        assert result["count"] == 0

    def test_detect_outliers(self):
        """Detects outliers with extreme values."""
        la = LatencyAnalyzer()
        samples = [LatencySample(0, 10) for _ in range(100)]
        samples.append(LatencySample(0, 10000))  # extreme outlier
        outliers = la.detect_outliers(samples, z_threshold=2.0)
        assert len(outliers) >= 1
        assert outliers[0].duration_ms == 10000

    def test_no_outliers_in_uniform(self):
        """Uniform data has no outliers at high threshold."""
        la = LatencyAnalyzer()
        samples = [LatencySample(0, 50) for _ in range(50)]
        outliers = la.detect_outliers(samples, z_threshold=3.0)
        assert len(outliers) == 0


# ── LittlesLaw ──


class TestLittlesLaw:
    def test_items_in_system(self):
        """L = lambda * W."""
        assert LittlesLaw.items_in_system(10, 0.5) == pytest.approx(5)

    def test_avg_time(self):
        """W = L / lambda."""
        assert LittlesLaw.avg_time(10, 5) == pytest.approx(0.5)

    def test_arrival_rate(self):
        """lambda = L / W."""
        assert LittlesLaw.arrival_rate(5, 0.5) == pytest.approx(10)

    def test_consistency(self):
        """All three formulas are consistent."""
        lam, W = 20, 0.1
        L = LittlesLaw.items_in_system(lam, W)
        assert LittlesLaw.avg_time(lam, L) == pytest.approx(W)
        assert LittlesLaw.arrival_rate(L, W) == pytest.approx(lam)

    def test_zero_arrival_rate(self):
        """Zero arrival rate gives zero time."""
        assert LittlesLaw.avg_time(0, 5) == 0.0


# ── MM1Queue ──


class TestMM1Queue:
    def test_utilization(self):
        """Utilization = lambda / mu."""
        q = MM1Queue(arrival_rate=80, service_rate=100)
        assert q.utilization() == pytest.approx(0.8)

    def test_avg_system_time(self):
        """W = 1 / (mu - lambda)."""
        q = MM1Queue(arrival_rate=80, service_rate=100)
        assert q.avg_system_time() == pytest.approx(1 / 20)

    def test_probability_empty(self):
        """P0 = 1 - rho."""
        q = MM1Queue(arrival_rate=30, service_rate=100)
        assert q.probability_empty() == pytest.approx(0.7)

    def test_unstable_queue(self):
        """Unstable queue (lambda >= mu) returns inf."""
        q = MM1Queue(arrival_rate=100, service_rate=100)
        assert q.avg_system_time() == float("inf")

    def test_avg_queue_length(self):
        """Lq = rho^2 / (1 - rho)."""
        q = MM1Queue(arrival_rate=80, service_rate=100)
        expected = 0.8 ** 2 / (1 - 0.8)
        assert q.avg_queue_length() == pytest.approx(expected)

    def test_littles_law_holds(self):
        """Little's law: L = lambda * W."""
        q = MM1Queue(arrival_rate=60, service_rate=100)
        L = q.avg_items_in_system()
        W = q.avg_system_time()
        assert L == pytest.approx(60 * W, abs=0.001)


# ── MMcQueue ──


class TestMMcQueue:
    def test_utilization(self):
        """Per-server utilization = lambda / (c * mu)."""
        q = MMcQueue(arrival_rate=80, service_rate=100, num_servers=2)
        assert q.utilization() == pytest.approx(0.4)

    def test_multi_server_faster(self):
        """More servers means lower wait time."""
        q1 = MMcQueue(arrival_rate=80, service_rate=100, num_servers=1)
        q2 = MMcQueue(arrival_rate=80, service_rate=100, num_servers=2)
        assert q2.avg_wait_time() < q1.avg_wait_time()

    def test_system_time_includes_service(self):
        """System time = wait time + service time."""
        q = MMcQueue(arrival_rate=50, service_rate=100, num_servers=2)
        service_time = 1 / 100
        assert q.avg_system_time() == pytest.approx(
            q.avg_wait_time() + service_time
        )


# ── CapacityPlanner ──


class TestCapacityPlanner:
    def test_project_load(self):
        """Load projection with 10% monthly growth."""
        cp = CapacityPlanner(current_load=100, growth_rate_monthly=0.1)
        assert cp.project_load(12) == pytest.approx(100 * 1.1 ** 12, rel=0.01)

    def test_time_to_exhaustion(self):
        """Correctly computes months until capacity is full."""
        cp = CapacityPlanner(current_load=100, growth_rate_monthly=0.1)
        months = cp.time_to_exhaustion(200)
        # 100 * 1.1^t = 200 => t = log(2) / log(1.1) ~= 7.27
        assert months == pytest.approx(7.27, abs=0.1)

    def test_recommend_scaling(self):
        """Recommend scaling returns a valid recommendation."""
        cp = CapacityPlanner(current_load=100, growth_rate_monthly=0.1)
        rec = cp.recommend_scaling(target_headroom=6)
        assert isinstance(rec, ScalingRecommendation)
        assert rec.target_instances > 0
        assert rec.estimated_cost > 0
