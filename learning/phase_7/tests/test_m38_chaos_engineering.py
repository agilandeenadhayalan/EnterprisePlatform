"""
Tests for M38: Chaos Engineering — failure injection, hypothesis testing, blast radius, game days.
"""

import random
import pytest

from m38_chaos_engineering.failure_injection import (
    FailureMode,
    FailureConfig,
    FailureInjector,
    NetworkFault,
    ResourceExhaustion,
)
from m38_chaos_engineering.hypothesis_testing import (
    SteadyStateMetric,
    SteadyStateHypothesis,
    ChaosExperiment,
    ExperimentResult,
)
from m38_chaos_engineering.blast_radius import (
    ServiceNode,
    Dependency,
    DependencyGraph,
    BlastRadiusAnalyzer,
    ImpactReport,
)
from m38_chaos_engineering.game_days import (
    GameDayPhase,
    RunbookStep,
    GameDayRunbook,
    GameDayRunner,
    GameDayReport,
)


# ── FailureInjector ──


class TestFailureInjector:
    def test_inject_returns_id(self):
        """Inject returns a unique injection ID."""
        fi = FailureInjector()
        config = FailureConfig(mode=FailureMode.cpu_stress, duration_seconds=60)
        injection_id = fi.inject(config)
        assert isinstance(injection_id, str)
        assert len(injection_id) > 0

    def test_inject_tracks_active(self):
        """Injected failures appear in active list."""
        fi = FailureInjector()
        config = FailureConfig(mode=FailureMode.network_latency, duration_seconds=30)
        fi.inject(config)
        active = fi.get_active_injections()
        assert len(active) == 1
        assert active[0]["mode"] == "network_latency"

    def test_rollback_removes_injection(self):
        """Rollback removes the injection."""
        fi = FailureInjector()
        config = FailureConfig(mode=FailureMode.disk_full, duration_seconds=60)
        injection_id = fi.inject(config)
        assert fi.rollback(injection_id) is True
        assert len(fi.get_active_injections()) == 0

    def test_rollback_unknown_returns_false(self):
        """Rolling back an unknown ID returns False."""
        fi = FailureInjector()
        assert fi.rollback("nonexistent") is False

    def test_invalid_intensity_raises(self):
        """Intensity outside [0, 1] raises ValueError."""
        fi = FailureInjector()
        config = FailureConfig(mode=FailureMode.cpu_stress, duration_seconds=60, intensity=1.5)
        with pytest.raises(ValueError):
            fi.inject(config)

    def test_multiple_injections(self):
        """Multiple injections are tracked independently."""
        fi = FailureInjector()
        id1 = fi.inject(FailureConfig(mode=FailureMode.cpu_stress, duration_seconds=30))
        id2 = fi.inject(FailureConfig(mode=FailureMode.memory_leak, duration_seconds=30))
        assert len(fi.get_active_injections()) == 2
        fi.rollback(id1)
        assert len(fi.get_active_injections()) == 1


# ── NetworkFault ──


class TestNetworkFault:
    def test_add_latency(self):
        """Adding latency increases the total latency."""
        nf = NetworkFault()
        nf.add_latency(100.0)
        result = nf.apply_to_request(50.0)
        assert result["latency_ms"] >= 150.0  # base + added

    def test_latency_with_jitter(self):
        """Jitter varies the added latency."""
        random.seed(42)
        nf = NetworkFault()
        nf.add_latency(100.0, jitter_ms=20.0)
        results = [nf.apply_to_request(50.0)["latency_ms"] for _ in range(100)]
        # Not all results should be identical due to jitter
        assert len(set(results)) > 1

    def test_packet_loss(self):
        """Packet loss drops some requests."""
        random.seed(42)
        nf = NetworkFault()
        nf.add_packet_loss(0.5)
        dropped = sum(
            1 for _ in range(1000)
            if nf.apply_to_request(10.0)["dropped"]
        )
        # Should drop roughly 50% +/- some variance
        assert 350 < dropped < 650

    def test_zero_loss_no_drops(self):
        """Zero loss rate means no drops."""
        nf = NetworkFault()
        nf.add_packet_loss(0.0)
        for _ in range(100):
            assert nf.apply_to_request(10.0)["dropped"] is False

    def test_partition(self):
        """Partitioned services are identified."""
        nf = NetworkFault()
        nf.simulate_partition(["service-a", "service-b"])
        assert nf.is_partitioned("service-a") is True
        assert nf.is_partitioned("service-c") is False

    def test_invalid_loss_rate_raises(self):
        """Loss rate outside [0, 1] raises ValueError."""
        nf = NetworkFault()
        with pytest.raises(ValueError):
            nf.add_packet_loss(1.5)


# ── ResourceExhaustion ──


class TestResourceExhaustion:
    def test_no_load_no_impact(self):
        """Zero load means no degradation."""
        re = ResourceExhaustion()
        impact = re.get_impact()
        assert impact["cpu_degradation_factor"] == 1.0
        assert impact["memory_degradation_factor"] == 1.0

    def test_cpu_load_increases_factor(self):
        """Higher CPU load increases degradation factor."""
        re = ResourceExhaustion()
        re.simulate_cpu_load(80.0)
        impact = re.get_impact()
        assert impact["cpu_degradation_factor"] > 1.0

    def test_memory_pressure_increases_factor(self):
        """Higher memory pressure increases degradation factor."""
        re = ResourceExhaustion()
        re.simulate_memory_pressure(90.0)
        impact = re.get_impact()
        assert impact["memory_degradation_factor"] > 1.0

    def test_combined_factor_multiplicative(self):
        """Combined factor is CPU * memory."""
        re = ResourceExhaustion()
        re.simulate_cpu_load(50.0)
        re.simulate_memory_pressure(50.0)
        impact = re.get_impact()
        expected = impact["cpu_degradation_factor"] * impact["memory_degradation_factor"]
        assert impact["combined_degradation_factor"] == pytest.approx(expected, abs=0.01)


# ── SteadyStateHypothesis ──


class TestSteadyStateHypothesis:
    def test_all_metrics_pass(self):
        """Hypothesis passes when all metrics are within range."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        h.add_metric(SteadyStateMetric("error_rate", (0, 0.01)))
        assert h.verify({"latency_ms": 100.0, "error_rate": 0.005}) is True

    def test_metric_out_of_range(self):
        """Hypothesis fails when a metric exceeds range."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        assert h.verify({"latency_ms": 300.0}) is False

    def test_missing_metric_is_violation(self):
        """Missing metric counts as violation."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        violations = h.get_violations({})
        assert len(violations) == 1
        assert violations[0]["reason"] == "missing"

    def test_tolerance_allows_slight_overshoot(self):
        """Tolerance allows values slightly beyond the range."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200), tolerance_percent=10.0))
        # 200 * 1.1 = 220 should pass
        assert h.verify({"latency_ms": 210.0}) is True

    def test_tolerance_exceeded_is_violation(self):
        """Values beyond tolerance are still violations."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200), tolerance_percent=5.0))
        # 200 * 1.05 = 210, so 220 should fail
        assert h.verify({"latency_ms": 220.0}) is False

    def test_multiple_violations(self):
        """Reports all violating metrics."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        h.add_metric(SteadyStateMetric("error_rate", (0, 0.01)))
        violations = h.get_violations({"latency_ms": 500.0, "error_rate": 0.05})
        assert len(violations) == 2


# ── ChaosExperiment ──


class TestChaosExperiment:
    def test_passing_experiment(self):
        """Experiment passes when system recovers to steady state."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        exp = ChaosExperiment("test", h)
        exp.record_baseline({"latency_ms": 100.0})
        exp.record_during({"latency_ms": 500.0})  # violation during chaos
        exp.record_after({"latency_ms": 120.0})   # recovered
        result = exp.analyze()
        assert result.passed is True

    def test_failing_experiment(self):
        """Experiment fails when system does not recover."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        exp = ChaosExperiment("test", h)
        exp.record_baseline({"latency_ms": 100.0})
        exp.record_during({"latency_ms": 500.0})
        exp.record_after({"latency_ms": 400.0})  # still violated
        result = exp.analyze()
        assert result.passed is False

    def test_bad_baseline_fails(self):
        """Experiment fails if baseline already violates hypothesis."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        exp = ChaosExperiment("test", h)
        exp.record_baseline({"latency_ms": 300.0})  # already bad
        exp.record_during({"latency_ms": 500.0})
        exp.record_after({"latency_ms": 150.0})
        result = exp.analyze()
        assert result.passed is False

    def test_result_has_measurements(self):
        """Result contains all three phases of measurements."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        exp = ChaosExperiment("test", h)
        exp.record_baseline({"latency_ms": 100.0})
        exp.record_during({"latency_ms": 300.0})
        exp.record_after({"latency_ms": 110.0})
        result = exp.analyze()
        assert "latency_ms" in result.baseline_measurements
        assert "latency_ms" in result.during_measurements
        assert "latency_ms" in result.after_measurements

    def test_recovery_time_when_recovered(self):
        """Recovery time is positive when system recovered from violations."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        exp = ChaosExperiment("test", h)
        exp.record_baseline({"latency_ms": 100.0})
        exp.record_during({"latency_ms": 500.0})
        exp.record_after({"latency_ms": 100.0})
        result = exp.analyze()
        assert result.recovery_time_ms > 0

    def test_violations_list(self):
        """Result violations list includes during-phase violations."""
        h = SteadyStateHypothesis()
        h.add_metric(SteadyStateMetric("latency_ms", (0, 200)))
        exp = ChaosExperiment("test", h)
        exp.record_baseline({"latency_ms": 100.0})
        exp.record_during({"latency_ms": 500.0})
        exp.record_after({"latency_ms": 100.0})
        result = exp.analyze()
        assert len(result.violations) > 0


# ── DependencyGraph ──


class TestDependencyGraph:
    @pytest.fixture
    def graph(self):
        g = DependencyGraph()
        g.add_service(ServiceNode("api-gateway", criticality=9, user_facing=True))
        g.add_service(ServiceNode("user-service", criticality=8, user_facing=False))
        g.add_service(ServiceNode("payment-service", criticality=10, user_facing=True))
        g.add_service(ServiceNode("db", criticality=10, user_facing=False))
        g.add_dependency(Dependency("api-gateway", "user-service", "sync"))
        g.add_dependency(Dependency("api-gateway", "payment-service", "sync"))
        g.add_dependency(Dependency("user-service", "db", "sync"))
        g.add_dependency(Dependency("payment-service", "db", "sync"))
        return g

    def test_get_downstream(self, graph):
        """Downstream of db includes services that depend on it."""
        downstream = graph.get_downstream("db")
        assert "user-service" in downstream
        assert "payment-service" in downstream

    def test_get_downstream_transitive(self, graph):
        """Downstream includes transitive dependents."""
        downstream = graph.get_downstream("db")
        assert "api-gateway" in downstream

    def test_get_upstream(self, graph):
        """Upstream returns direct dependencies."""
        upstream = graph.get_upstream("api-gateway")
        assert "user-service" in upstream
        assert "payment-service" in upstream

    def test_topological_sort(self, graph):
        """Topological sort puts dependencies before dependents."""
        order = graph.topological_sort()
        assert order.index("db") < order.index("user-service")
        assert order.index("db") < order.index("payment-service")

    def test_no_downstream_for_leaf(self, graph):
        """Leaf service (api-gateway) has no downstream."""
        downstream = graph.get_downstream("api-gateway")
        assert len(downstream) == 0

    def test_get_service(self, graph):
        """Retrieves service node by name."""
        svc = graph.get_service("db")
        assert svc is not None
        assert svc.criticality == 10


# ── BlastRadiusAnalyzer ──


class TestBlastRadiusAnalyzer:
    @pytest.fixture
    def analyzer(self):
        g = DependencyGraph()
        g.add_service(ServiceNode("api", criticality=9, user_facing=True))
        g.add_service(ServiceNode("svc-a", criticality=7, user_facing=False))
        g.add_service(ServiceNode("svc-b", criticality=5, user_facing=True))
        g.add_service(ServiceNode("db", criticality=10, user_facing=False))
        g.add_dependency(Dependency("api", "svc-a", "sync"))
        g.add_dependency(Dependency("api", "svc-b", "sync"))
        g.add_dependency(Dependency("svc-a", "db", "sync"))
        return BlastRadiusAnalyzer(g)

    def test_analyze_returns_report(self, analyzer):
        """Analyze returns an ImpactReport."""
        report = analyzer.analyze("db")
        assert isinstance(report, ImpactReport)
        assert report.target == "db"

    def test_affected_services(self, analyzer):
        """Report includes affected services."""
        report = analyzer.analyze("db")
        assert "svc-a" in report.affected_services

    def test_cascade_depth(self, analyzer):
        """Cascade depth counts levels of propagation."""
        report = analyzer.analyze("db")
        assert report.cascade_depth >= 1

    def test_impact_score_positive(self, analyzer):
        """Impact score is positive for a critical service."""
        score = analyzer.get_impact_score("db")
        assert score > 0

    def test_user_impact_percentage(self, analyzer):
        """User impact is percentage of user-facing services affected."""
        percent = analyzer.get_affected_users_estimate("db")
        assert 0 <= percent <= 100


# ── GameDayRunbook ──


class TestGameDayRunbook:
    def test_add_step(self):
        """Steps can be added to the runbook."""
        rb = GameDayRunbook()
        step = rb.add_step("Kill DB", "Failover activates", "Restart DB")
        assert step.step_number == 1
        assert len(rb) == 1

    def test_execute_step(self):
        """Steps can be executed and recorded."""
        rb = GameDayRunbook()
        rb.add_step("Kill DB", "Failover activates", "Restart DB")
        assert rb.execute_step(1, "Failover activated in 30s", True) is True

    def test_progress(self):
        """Progress tracks executed vs total steps."""
        rb = GameDayRunbook()
        rb.add_step("Step 1", "OK", "Undo 1")
        rb.add_step("Step 2", "OK", "Undo 2")
        rb.execute_step(1, "Done", True)
        assert rb.get_progress() == pytest.approx(0.5)

    def test_needs_rollback_when_failed(self):
        """Runbook needs rollback if any step failed."""
        rb = GameDayRunbook()
        rb.add_step("Step 1", "OK", "Undo 1")
        rb.execute_step(1, "Failed", False)
        assert rb.needs_rollback() is True

    def test_no_rollback_when_all_pass(self):
        """No rollback needed when all steps pass."""
        rb = GameDayRunbook()
        rb.add_step("Step 1", "OK", "Undo 1")
        rb.execute_step(1, "Done", True)
        assert rb.needs_rollback() is False

    def test_empty_runbook_progress(self):
        """Empty runbook has zero progress."""
        rb = GameDayRunbook()
        assert rb.get_progress() == 0.0


# ── GameDayRunner ──


class TestGameDayRunner:
    def test_start_enters_planning(self):
        """Starting a game day enters the planning phase."""
        rb = GameDayRunbook()
        runner = GameDayRunner("Test Day", rb)
        phase = runner.start()
        assert phase == GameDayPhase.planning

    def test_advance_phase(self):
        """Advancing moves to the next phase."""
        rb = GameDayRunbook()
        runner = GameDayRunner("Test Day", rb)
        runner.start()
        phase = runner.advance_phase()
        assert phase == GameDayPhase.briefing

    def test_advance_through_all_phases(self):
        """Can advance through all six phases."""
        rb = GameDayRunbook()
        runner = GameDayRunner("Test Day", rb)
        runner.start()
        phases = []
        while True:
            p = runner.advance_phase()
            if p is None:
                break
            phases.append(p)
        assert len(phases) == 5  # 5 advances after planning

    def test_add_observation(self):
        """Observations are recorded."""
        rb = GameDayRunbook()
        runner = GameDayRunner("Test Day", rb)
        runner.start()
        runner.add_observation("Latency spiked to 500ms")
        report = runner.generate_report()
        assert "Latency spiked to 500ms" in report.observations

    def test_generate_report(self):
        """Report includes pass rate and observations."""
        rb = GameDayRunbook()
        rb.add_step("Kill pod", "Restart", "Scale up")
        rb.execute_step(1, "Restarted OK", True)
        runner = GameDayRunner("Test Day", rb, ["alice", "bob"])
        runner.start()
        report = runner.generate_report()
        assert isinstance(report, GameDayReport)
        assert report.pass_rate == 1.0

    def test_report_with_failures(self):
        """Report reflects step failures."""
        rb = GameDayRunbook()
        rb.add_step("Step 1", "OK", "Undo")
        rb.add_step("Step 2", "OK", "Undo")
        rb.execute_step(1, "OK", True)
        rb.execute_step(2, "Failed", False)
        runner = GameDayRunner("Test Day", rb)
        runner.start()
        report = runner.generate_report()
        assert report.pass_rate == pytest.approx(0.5)


# ── ImpactReport ──


class TestImpactReport:
    def test_create_report(self):
        """ImpactReport can be created with all fields."""
        report = ImpactReport(
            target="db",
            affected_services=["svc-a", "api"],
            cascade_depth=2,
            impact_score=15.0,
            user_impact_percent=50.0,
        )
        assert report.target == "db"
        assert len(report.affected_services) == 2

    def test_empty_affected(self):
        """Report with no affected services."""
        report = ImpactReport(
            target="leaf",
            affected_services=[],
            cascade_depth=0,
            impact_score=5.0,
            user_impact_percent=0.0,
        )
        assert report.cascade_depth == 0

    def test_high_impact(self):
        """High-criticality failure has high impact score."""
        report = ImpactReport(
            target="db",
            affected_services=["a", "b", "c", "d"],
            cascade_depth=3,
            impact_score=45.0,
            user_impact_percent=80.0,
        )
        assert report.impact_score > 10.0

    def test_user_impact_range(self):
        """User impact is a valid percentage."""
        report = ImpactReport(
            target="db",
            affected_services=["a"],
            cascade_depth=1,
            impact_score=10.0,
            user_impact_percent=25.0,
        )
        assert 0 <= report.user_impact_percent <= 100
