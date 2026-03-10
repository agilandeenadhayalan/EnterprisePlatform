"""
Tests for M37: Multi-Region Architecture — CRDTs, replication, geo-routing, failover.
"""

import time
import pytest

from m37_multi_region.crdts import (
    GCounter,
    PNCounter,
    LWWRegister,
    ORSet,
    VectorClock,
)
from m37_multi_region.active_active import (
    ReplicationMode,
    RegionReplica,
    ReplicationTopology,
    ActiveActiveCluster,
    ConflictDetector,
)
from m37_multi_region.geo_routing import (
    GeoCoordinate,
    RegionEndpoint,
    GeoRouter,
    LatencyMatrix,
)
from m37_multi_region.region_failover import (
    HealthStatus,
    FailoverPhase,
    HealthChecker,
    FailoverStateMachine,
    FailoverOrchestrator,
)


# ── GCounter ──


class TestGCounter:
    def test_single_increment(self):
        """Single increment produces value 1."""
        gc = GCounter("node_a")
        gc.increment()
        assert gc.value() == 1

    def test_multiple_increments(self):
        """Multiple increments accumulate."""
        gc = GCounter("node_a")
        gc.increment(5)
        gc.increment(3)
        assert gc.value() == 8

    def test_merge_two_counters(self):
        """Merge takes max of each node's counter."""
        a = GCounter("node_a")
        b = GCounter("node_b")
        a.increment(3)
        b.increment(5)
        a.merge(b)
        assert a.value() == 8  # 3 + 5

    def test_merge_is_commutative(self):
        """merge(A, B) produces same value as merge(B, A)."""
        a = GCounter("node_a")
        b = GCounter("node_b")
        a.increment(3)
        b.increment(7)

        a_copy = GCounter("node_a")
        a_copy.increment(3)
        b_copy = GCounter("node_b")
        b_copy.increment(7)

        a.merge(b)
        b_copy.merge(a_copy)
        assert a.value() == b_copy.value()

    def test_merge_is_idempotent(self):
        """merge(A, A) produces A."""
        a = GCounter("node_a")
        a.increment(5)
        before = a.value()
        a.merge(a)
        assert a.value() == before

    def test_state_returns_copy(self):
        """state() returns dict of node counters."""
        gc = GCounter("node_a")
        gc.increment(4)
        state = gc.state()
        assert state == {"node_a": 4}
        assert isinstance(state, dict)


# ── PNCounter ──


class TestPNCounter:
    def test_increment_only(self):
        """Increment increases the value."""
        pn = PNCounter("node_a")
        pn.increment(5)
        assert pn.value() == 5

    def test_decrement_only(self):
        """Decrement decreases the value."""
        pn = PNCounter("node_a")
        pn.decrement(3)
        assert pn.value() == -3

    def test_increment_and_decrement(self):
        """Increment and decrement combine correctly."""
        pn = PNCounter("node_a")
        pn.increment(10)
        pn.decrement(3)
        assert pn.value() == 7

    def test_merge_pn_counters(self):
        """Merge combines positive and negative counters."""
        a = PNCounter("node_a")
        b = PNCounter("node_b")
        a.increment(10)
        b.decrement(3)
        a.merge(b)
        assert a.value() == 7

    def test_merge_preserves_semantics(self):
        """Merged PNCounter reflects all operations."""
        a = PNCounter("node_a")
        b = PNCounter("node_b")
        a.increment(5)
        a.decrement(2)
        b.increment(3)
        b.decrement(1)
        a.merge(b)
        # a: 5-2=3, b: 3-1=2, merged: 5
        assert a.value() == 5


# ── LWWRegister ──


class TestLWWRegister:
    def test_set_and_get(self):
        """Set stores the value, get retrieves it."""
        reg = LWWRegister()
        reg.set("hello", timestamp=1.0)
        assert reg.get() == "hello"

    def test_later_write_wins(self):
        """Higher timestamp overwrites lower."""
        reg = LWWRegister()
        reg.set("first", timestamp=1.0)
        reg.set("second", timestamp=2.0)
        assert reg.get() == "second"

    def test_earlier_write_ignored(self):
        """Lower timestamp does not overwrite higher."""
        reg = LWWRegister()
        reg.set("second", timestamp=2.0)
        reg.set("first", timestamp=1.0)
        assert reg.get() == "second"

    def test_merge_keeps_later(self):
        """Merge keeps the value with the higher timestamp."""
        a = LWWRegister()
        b = LWWRegister()
        a.set("old", timestamp=1.0)
        b.set("new", timestamp=2.0)
        a.merge(b)
        assert a.get() == "new"

    def test_merge_does_not_regress(self):
        """Merge with older value does not change current value."""
        a = LWWRegister()
        b = LWWRegister()
        a.set("new", timestamp=2.0)
        b.set("old", timestamp=1.0)
        a.merge(b)
        assert a.get() == "new"


# ── ORSet ──


class TestORSet:
    def test_add_element(self):
        """Adding an element makes it present."""
        s = ORSet()
        s.add("x")
        assert "x" in s.elements()

    def test_remove_element(self):
        """Removing an element makes it absent."""
        s = ORSet()
        s.add("x")
        s.remove("x")
        assert "x" not in s.elements()

    def test_add_multiple_elements(self):
        """Multiple distinct elements coexist."""
        s = ORSet()
        s.add("a")
        s.add("b")
        s.add("c")
        assert s.elements() == {"a", "b", "c"}

    def test_merge_adds_from_both(self):
        """Merge includes elements from both sets."""
        a = ORSet()
        b = ORSet()
        a.add("x")
        b.add("y")
        a.merge(b)
        assert "x" in a.elements()
        assert "y" in a.elements()

    def test_merge_add_wins(self):
        """Concurrent add and remove: add wins (add-wins semantics)."""
        a = ORSet()
        b = ORSet()
        a.add("x")
        b.add("x")
        a.remove("x")  # remove on a, but b still has its own tag
        a.merge(b)
        assert "x" in a.elements()

    def test_remove_then_merge_empty(self):
        """Remove on both replicas removes the element after merge."""
        a = ORSet()
        b = ORSet()
        a.add("x")
        b.merge(a)  # b now has x with same tags
        a.remove("x")
        b.remove("x")
        a.merge(b)
        assert "x" not in a.elements()


# ── VectorClock ──


class TestVectorClock:
    def test_increment(self):
        """Increment advances one component."""
        vc = VectorClock()
        vc.increment("a")
        assert vc.state() == {"a": 1}

    def test_compare_equal(self):
        """Identical clocks are equal."""
        a = VectorClock()
        b = VectorClock()
        a.increment("x")
        b.increment("x")
        assert a.compare(b) == "equal"

    def test_compare_before(self):
        """A clock with smaller components is 'before'."""
        a = VectorClock()
        b = VectorClock()
        a.increment("x")
        b.increment("x")
        b.increment("x")
        assert a.compare(b) == "before"

    def test_compare_after(self):
        """A clock with larger components is 'after'."""
        a = VectorClock()
        b = VectorClock()
        a.increment("x")
        a.increment("x")
        b.increment("x")
        assert a.compare(b) == "after"

    def test_compare_concurrent(self):
        """Incomparable clocks are concurrent."""
        a = VectorClock()
        b = VectorClock()
        a.increment("x")
        b.increment("y")
        assert a.compare(b) == "concurrent"


# ── ActiveActiveCluster ──


class TestActiveActiveCluster:
    def test_add_region(self):
        """Regions can be added to the cluster."""
        cluster = ActiveActiveCluster()
        cluster.add_region("us-east-1")
        cluster.add_region("eu-west-1")
        assert len(cluster.replicas) == 2

    def test_write_and_read(self):
        """Write to a region, read it back."""
        cluster = ActiveActiveCluster()
        cluster.add_region("us-east-1")
        cluster.write("key1", "value1", "us-east-1")
        assert cluster.read("key1") == "value1"

    def test_write_unknown_region_raises(self):
        """Writing to an unknown region raises ValueError."""
        cluster = ActiveActiveCluster()
        with pytest.raises(ValueError):
            cluster.write("key1", "value1", "unknown")

    def test_replicate_propagates_writes(self):
        """Replicate propagates writes to all regions."""
        cluster = ActiveActiveCluster()
        cluster.add_region("us-east-1")
        cluster.add_region("eu-west-1")
        cluster.write("key1", "value1", "us-east-1")
        count = cluster.replicate()
        assert count >= 1

    def test_read_after_replication(self):
        """After replication, key is readable from both regions."""
        cluster = ActiveActiveCluster()
        cluster.add_region("us-east-1")
        cluster.add_region("eu-west-1")
        cluster.write("key1", "value1", "us-east-1")
        cluster.replicate()
        assert cluster.read("key1", "all") == "value1"

    def test_version_increments_on_write(self):
        """Each write increments the region's version."""
        cluster = ActiveActiveCluster()
        cluster.add_region("us-east-1")
        cluster.write("k1", "v1", "us-east-1")
        cluster.write("k2", "v2", "us-east-1")
        assert cluster.replicas["us-east-1"].data_version == 2

    def test_lag_reflects_pending_entries(self):
        """Lag increases with unreplicated entries."""
        cluster = ActiveActiveCluster()
        cluster.add_region("us-east-1")
        cluster.add_region("eu-west-1")
        cluster.write("k1", "v1", "us-east-1")
        lag = cluster.get_lag("eu-west-1")
        assert lag > 0


# ── ConflictDetector ──


class TestConflictDetector:
    def test_equal_versions(self):
        """Identical version vectors are equal."""
        cd = ConflictDetector()
        assert cd.check({"a": 1}, {"a": 1}) == "equal"

    def test_a_newer(self):
        """A dominates B means A is newer."""
        cd = ConflictDetector()
        assert cd.check({"a": 2, "b": 1}, {"a": 1, "b": 1}) == "a_newer"

    def test_b_newer(self):
        """B dominates A means B is newer."""
        cd = ConflictDetector()
        assert cd.check({"a": 1, "b": 1}, {"a": 2, "b": 1}) == "b_newer"

    def test_concurrent(self):
        """Neither dominates means concurrent (conflict)."""
        cd = ConflictDetector()
        assert cd.check({"a": 2, "b": 1}, {"a": 1, "b": 2}) == "concurrent"


# ── GeoRouter ──


class TestGeoRouter:
    @pytest.fixture
    def router(self):
        r = GeoRouter()
        r.add_region(RegionEndpoint(
            code="us-east", name="US East",
            coordinate=GeoCoordinate(39.0, -77.0),
            latency_ms=10.0, load_factor=0.3,
        ))
        r.add_region(RegionEndpoint(
            code="eu-west", name="EU West",
            coordinate=GeoCoordinate(53.0, -6.0),
            latency_ms=50.0, load_factor=0.5,
        ))
        r.add_region(RegionEndpoint(
            code="ap-east", name="Asia Pacific",
            coordinate=GeoCoordinate(35.0, 139.0),
            latency_ms=80.0, load_factor=0.2,
        ))
        return r

    def test_route_by_distance_nearest(self, router):
        """Routes to nearest region by distance."""
        # New York: 40.7, -74.0 — closest to us-east
        result = router.route_by_distance(40.7, -74.0)
        assert result is not None
        assert result.code == "us-east"

    def test_route_by_distance_europe(self, router):
        """European user routes to EU region."""
        # London: 51.5, -0.1
        result = router.route_by_distance(51.5, -0.1)
        assert result is not None
        assert result.code == "eu-west"

    def test_route_by_latency(self, router):
        """Routes to region with lowest latency."""
        result = router.route_by_latency(0.0, 0.0)
        assert result is not None
        assert result.code == "us-east"  # lowest latency_ms=10

    def test_route_weighted(self, router):
        """Weighted routing produces a valid region."""
        result = router.route_weighted(40.7, -74.0)
        assert result is not None
        assert result.code in ["us-east", "eu-west", "ap-east"]

    def test_inactive_region_excluded(self, router):
        """Inactive regions are not routed to."""
        router._regions["us-east"].status = "inactive"
        result = router.route_by_distance(40.7, -74.0)
        assert result is not None
        assert result.code != "us-east"

    def test_no_active_regions_returns_none(self):
        """Returns None when no active regions exist."""
        r = GeoRouter()
        assert r.route_by_distance(0.0, 0.0) is None


# ── LatencyMatrix ──


class TestLatencyMatrix:
    def test_update_and_get(self):
        """Records and retrieves latency between regions."""
        lm = LatencyMatrix()
        lm.update("us-east", "eu-west", 85.0)
        assert lm.get_latency("us-east", "eu-west") == 85.0

    def test_get_best_path(self):
        """Returns the region with lowest latency."""
        lm = LatencyMatrix()
        lm.update("us-east", "eu-west", 85.0)
        lm.update("us-east", "ap-east", 150.0)
        assert lm.get_best_path("us-east") == "eu-west"

    def test_unknown_source_returns_none(self):
        """Unknown source region returns None."""
        lm = LatencyMatrix()
        assert lm.get_best_path("unknown") is None

    def test_get_all_from(self):
        """Returns all measured latencies from a source."""
        lm = LatencyMatrix()
        lm.update("us-east", "eu-west", 85.0)
        lm.update("us-east", "ap-east", 150.0)
        all_from = lm.get_all_from("us-east")
        assert len(all_from) == 2
        assert all_from["eu-west"] == 85.0


# ── HealthChecker ──


class TestHealthChecker:
    def test_healthy_by_default(self):
        """New region with no checks is healthy."""
        hc = HealthChecker()
        hc.record_check("us-east", True)
        assert hc.get_status("us-east") == HealthStatus.healthy

    def test_degraded_after_failures(self):
        """Region becomes degraded after threshold failures."""
        hc = HealthChecker()
        hc.record_check("us-east", False)
        assert hc.get_status("us-east") == HealthStatus.degraded

    def test_unhealthy_after_more_failures(self):
        """Region becomes unhealthy after more failures."""
        hc = HealthChecker()
        for _ in range(3):
            hc.record_check("us-east", False)
        assert hc.get_status("us-east") == HealthStatus.unhealthy

    def test_dead_after_many_failures(self):
        """Region becomes dead after many failures."""
        hc = HealthChecker()
        for _ in range(5):
            hc.record_check("us-east", False)
        assert hc.get_status("us-east") == HealthStatus.dead

    def test_success_resets_failures(self):
        """A success resets the consecutive failure count."""
        hc = HealthChecker()
        for _ in range(4):
            hc.record_check("us-east", False)
        hc.record_check("us-east", True)
        assert hc.get_status("us-east") == HealthStatus.healthy


# ── FailoverStateMachine ──


class TestFailoverStateMachine:
    def test_starts_in_monitoring(self):
        """State machine starts in monitoring phase."""
        fsm = FailoverStateMachine()
        assert fsm.get_current_phase() == FailoverPhase.monitoring

    def test_valid_transition(self):
        """Valid transitions succeed."""
        fsm = FailoverStateMachine()
        assert fsm.transition(FailoverPhase.detecting) is True
        assert fsm.get_current_phase() == FailoverPhase.detecting

    def test_invalid_transition(self):
        """Invalid transitions are rejected."""
        fsm = FailoverStateMachine()
        assert fsm.transition(FailoverPhase.promoting) is False
        assert fsm.get_current_phase() == FailoverPhase.monitoring

    def test_full_failover_sequence(self):
        """Complete failover sequence through all phases."""
        fsm = FailoverStateMachine(cooldown_seconds=0)
        assert fsm.transition(FailoverPhase.detecting) is True
        assert fsm.transition(FailoverPhase.draining) is True
        assert fsm.transition(FailoverPhase.promoting) is True
        assert fsm.transition(FailoverPhase.verifying) is True
        assert fsm.transition(FailoverPhase.completed) is True
        assert fsm.get_current_phase() == FailoverPhase.completed

    def test_history_tracked(self):
        """Transitions are recorded in history."""
        fsm = FailoverStateMachine()
        fsm.transition(FailoverPhase.detecting)
        history = fsm.get_history()
        assert len(history) == 1
        assert history[0]["from"] == "monitoring"
        assert history[0]["to"] == "detecting"
