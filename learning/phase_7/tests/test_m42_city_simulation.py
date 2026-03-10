"""
Tests for M42: City Simulation (Capstone) — agents, engine, dispatch, pricing, analytics.
"""

import pytest

from m42_city_simulation.agent_model import (
    Position,
    AgentState,
    DriverAgent,
    RiderAgent,
    RideRequest,
)
from m42_city_simulation.simulation_engine import (
    SimulationClock,
    Event,
    EventQueue,
    SimulationEngine,
    SimulationConfig,
)
from m42_city_simulation.city_integration import (
    NearestDriverDispatch,
    ScoredDispatch,
    DynamicPricing,
    ETAEstimator,
    CityOrchestrator,
)
from m42_city_simulation.analytics_pipeline import (
    TickMetrics,
    MetricsCollector,
    KPICalculator,
    SimulationReport,
    ScenarioComparator,
)


# ── Position ──


class TestPosition:
    def test_distance_same_point(self):
        """Distance to self is zero."""
        p = Position(3.0, 4.0)
        assert p.distance_to(p) == pytest.approx(0.0)

    def test_distance_known(self):
        """3-4-5 triangle distance."""
        a = Position(0.0, 0.0)
        b = Position(3.0, 4.0)
        assert a.distance_to(b) == pytest.approx(5.0)

    def test_distance_symmetric(self):
        """Distance is symmetric."""
        a = Position(1.0, 2.0)
        b = Position(4.0, 6.0)
        assert a.distance_to(b) == pytest.approx(b.distance_to(a))


# ── DriverAgent ──


class TestDriverAgent:
    def test_initial_state(self):
        """New driver starts idle."""
        driver = DriverAgent("d1", Position(0, 0))
        assert driver.state == AgentState.IDLE
        assert driver.is_available()

    def test_accept_ride(self):
        """Accepting a ride transitions to EN_ROUTE_PICKUP."""
        driver = DriverAgent("d1", Position(0, 0))
        driver.accept_ride(Position(3, 4), Position(10, 10))
        assert driver.state == AgentState.EN_ROUTE_PICKUP
        assert not driver.is_available()

    def test_step_moves_toward_destination(self):
        """Step moves driver toward pickup."""
        driver = DriverAgent("d1", Position(0, 0), speed=1.0)
        driver.accept_ride(Position(5, 0), Position(10, 0))
        driver.step(1)
        assert driver.position.x == pytest.approx(1.0)
        assert driver.position.y == pytest.approx(0.0)

    def test_arrival_at_pickup(self):
        """Driver transitions to EN_ROUTE_DROPOFF at pickup."""
        driver = DriverAgent("d1", Position(0, 0), speed=5.0)
        driver.accept_ride(Position(3, 0), Position(10, 0))
        driver.step(1)  # speed=5 > distance=3, arrives
        assert driver.state == AgentState.EN_ROUTE_DROPOFF

    def test_full_ride_completion(self):
        """Driver completes full ride lifecycle."""
        driver = DriverAgent("d1", Position(0, 0), speed=100.0)
        driver.accept_ride(Position(1, 0), Position(2, 0))
        driver.step(1)  # Arrive at pickup
        driver.step(2)  # Arrive at dropoff
        assert driver.state == AgentState.IDLE
        assert driver.is_available()

    def test_get_eta(self):
        """ETA = distance / speed."""
        driver = DriverAgent("d1", Position(0, 0), speed=2.0)
        target = Position(6, 8)  # distance = 10
        assert driver.get_eta(target) == pytest.approx(5.0)


# ── RiderAgent ──


class TestRiderAgent:
    def test_request_ride(self):
        """Requesting a ride transitions to WAITING."""
        rider = RiderAgent("r1", Position(1, 1), patience_ticks=5)
        request = rider.request_ride(Position(5, 5))
        assert rider.state == AgentState.WAITING
        assert rider.is_waiting()
        assert request.rider_id == "r1"

    def test_patience_countdown(self):
        """Rider cancels after patience expires."""
        rider = RiderAgent("r1", Position(0, 0), patience_ticks=3)
        rider.request_ride(Position(5, 5))
        rider.step(1)
        rider.step(2)
        assert rider.is_waiting()
        rider.step(3)  # patience exhausted
        assert not rider.is_waiting()
        assert rider.state == AgentState.IDLE

    def test_initial_state(self):
        """New rider starts idle."""
        rider = RiderAgent("r1", Position(0, 0))
        assert rider.state == AgentState.IDLE
        assert not rider.is_waiting()

    def test_ride_request_fields(self):
        """RideRequest has correct fields."""
        rider = RiderAgent("r1", Position(1, 2))
        req = rider.request_ride(Position(5, 6))
        assert req.pickup.x == pytest.approx(1.0)
        assert req.dropoff.y == pytest.approx(6.0)
        assert req.status == "pending"

    def test_completed_check(self):
        """Rider is_completed checks COMPLETED state."""
        rider = RiderAgent("r1", Position(0, 0))
        assert not rider.is_completed()
        rider.state = AgentState.COMPLETED
        assert rider.is_completed()


# ── RideRequest ──


class TestRideRequest:
    def test_defaults(self):
        """RideRequest has correct defaults."""
        req = RideRequest("r1", "rider1", Position(0, 0), Position(5, 5))
        assert req.status == "pending"
        assert req.assigned_driver_id is None

    def test_assignment(self):
        """Request can be assigned to a driver."""
        req = RideRequest("r1", "rider1", Position(0, 0), Position(5, 5))
        req.assigned_driver_id = "d1"
        req.status = "assigned"
        assert req.assigned_driver_id == "d1"
        assert req.status == "assigned"

    def test_positions(self):
        """Pickup and dropoff positions are stored."""
        req = RideRequest("r1", "rider1", Position(1, 2), Position(3, 4))
        assert req.pickup.distance_to(req.dropoff) == pytest.approx(
            Position(1, 2).distance_to(Position(3, 4))
        )


# ── SimulationClock ──


class TestSimulationClock:
    def test_initial_state(self):
        """Clock starts at tick 0."""
        clock = SimulationClock(tick_duration_seconds=2.0)
        assert clock.current_tick == 0
        assert clock.elapsed_seconds() == 0.0

    def test_advance(self):
        """Advancing increments tick and elapsed time."""
        clock = SimulationClock(tick_duration_seconds=1.5)
        clock.advance()
        assert clock.current_tick == 1
        assert clock.elapsed_seconds() == pytest.approx(1.5)

    def test_multiple_advances(self):
        """Multiple advances accumulate correctly."""
        clock = SimulationClock(tick_duration_seconds=0.5)
        for _ in range(10):
            clock.advance()
        assert clock.current_tick == 10
        assert clock.elapsed_seconds() == pytest.approx(5.0)


# ── EventQueue ──


class TestEventQueue:
    def test_schedule_and_get(self):
        """Scheduled events are retrieved at their tick."""
        eq = EventQueue()
        eq.schedule(Event(tick=5, event_type="request"))
        events = eq.get_events(5)
        assert len(events) == 1
        assert events[0].event_type == "request"

    def test_empty_tick(self):
        """No events at unscheduled tick."""
        eq = EventQueue()
        eq.schedule(Event(tick=3, event_type="x"))
        assert eq.get_events(1) == []

    def test_is_empty(self):
        """Queue reports empty correctly."""
        eq = EventQueue()
        assert eq.is_empty()
        eq.schedule(Event(tick=1, event_type="test"))
        assert not eq.is_empty()

    def test_peek(self):
        """Peek returns earliest event without removing."""
        eq = EventQueue()
        eq.schedule(Event(tick=10, event_type="late"))
        eq.schedule(Event(tick=2, event_type="early"))
        peeked = eq.peek()
        assert peeked.event_type == "early"
        assert not eq.is_empty()  # Not removed


# ── SimulationEngine ──


class TestSimulationEngine:
    def test_add_agent(self):
        """Agents can be added to the engine."""
        engine = SimulationEngine()
        driver = DriverAgent("d1", Position(0, 0))
        engine.add_agent(driver)
        state = engine.get_state()
        assert state["num_agents"] == 1

    def test_step_advances_clock(self):
        """Stepping advances the clock."""
        engine = SimulationEngine()
        engine.step()
        assert engine.clock.current_tick == 1

    def test_run_multiple_ticks(self):
        """Run executes the correct number of ticks."""
        engine = SimulationEngine()
        results = engine.run(5)
        assert len(results) == 5
        assert engine.clock.current_tick == 5

    def test_agent_step_called(self):
        """Agent step is called during engine step."""
        engine = SimulationEngine()
        driver = DriverAgent("d1", Position(0, 0), speed=1.0)
        driver.accept_ride(Position(10, 0), Position(20, 0))
        engine.add_agent(driver)
        engine.step()
        # Driver should have moved
        assert driver.position.x > 0

    def test_event_processing(self):
        """Events are processed at their scheduled tick."""
        engine = SimulationEngine()
        engine.event_queue.schedule(Event(tick=2, event_type="test_event", data={"key": "val"}))
        engine.step()  # tick 1
        engine.step()  # tick 2 — event processed
        assert engine.clock.current_tick == 2

    def test_state_includes_agent_states(self):
        """State reports agent state distribution."""
        engine = SimulationEngine()
        engine.add_agent(DriverAgent("d1", Position(0, 0)))
        engine.add_agent(DriverAgent("d2", Position(5, 5)))
        state = engine.get_state()
        assert state["agent_states"]["idle"] == 2


# ── NearestDriverDispatch ──


class TestNearestDriverDispatch:
    def test_nearest_assigned(self):
        """Nearest driver by distance is assigned."""
        dispatch = NearestDriverDispatch()
        d1 = DriverAgent("d1", Position(0, 0))
        d2 = DriverAgent("d2", Position(10, 10))
        req = RideRequest("r1", "rider1", Position(1, 1), Position(5, 5))
        result = dispatch.assign(req, [d1, d2])
        assert result == "d1"

    def test_no_drivers(self):
        """No available drivers returns None."""
        dispatch = NearestDriverDispatch()
        req = RideRequest("r1", "rider1", Position(0, 0), Position(5, 5))
        assert dispatch.assign(req, []) is None

    def test_equidistant_drivers(self):
        """Equidistant drivers — first one wins."""
        dispatch = NearestDriverDispatch()
        d1 = DriverAgent("d1", Position(1, 0))
        d2 = DriverAgent("d2", Position(0, 1))
        req = RideRequest("r1", "rider1", Position(0, 0), Position(5, 5))
        result = dispatch.assign(req, [d1, d2])
        assert result in ["d1", "d2"]

    def test_single_driver(self):
        """Single driver is always assigned."""
        dispatch = NearestDriverDispatch()
        d = DriverAgent("d1", Position(100, 100))
        req = RideRequest("r1", "rider1", Position(0, 0), Position(5, 5))
        assert dispatch.assign(req, [d]) == "d1"


# ── ScoredDispatch ──


class TestScoredDispatch:
    def test_score_prefers_closer(self):
        """Closer driver gets higher score."""
        dispatch = ScoredDispatch()
        d1 = DriverAgent("d1", Position(1, 0))
        d2 = DriverAgent("d2", Position(10, 0))
        req = RideRequest("r1", "rider1", Position(0, 0), Position(5, 5))
        assert dispatch.score(d1, req) > dispatch.score(d2, req)

    def test_assign_best_score(self):
        """Highest-scoring driver is assigned."""
        dispatch = ScoredDispatch()
        d1 = DriverAgent("d1", Position(1, 0))
        d2 = DriverAgent("d2", Position(10, 0))
        req = RideRequest("r1", "rider1", Position(0, 0), Position(5, 5))
        result = dispatch.assign(req, [d1, d2])
        assert result == "d1"

    def test_no_drivers(self):
        """No drivers returns None."""
        dispatch = ScoredDispatch()
        req = RideRequest("r1", "rider1", Position(0, 0), Position(5, 5))
        assert dispatch.assign(req, []) is None


# ── DynamicPricing ──


class TestDynamicPricing:
    def test_base_fare(self):
        """Fare includes base + distance + time."""
        pricing = DynamicPricing(base_fare=2.0, per_km_rate=1.5, per_min_rate=0.25)
        fare = pricing.calculate(distance_km=10, duration_min=20)
        expected = (2.0 + 10 * 1.5 + 20 * 0.25)
        assert fare == pytest.approx(expected)

    def test_surge_multiplier(self):
        """Surge multiplier increases fare."""
        pricing = DynamicPricing(base_fare=2.0, per_km_rate=1.0, per_min_rate=0.5)
        normal = pricing.calculate(5, 10)
        surged = pricing.calculate(5, 10, surge_multiplier=2.0)
        assert surged == pytest.approx(normal * 2.0)

    def test_surge_balanced(self):
        """Equal supply and demand = no surge."""
        pricing = DynamicPricing(base_fare=2.0, per_km_rate=1.0, per_min_rate=0.5)
        assert pricing.get_surge(supply=10, demand=10) == pytest.approx(1.0)

    def test_surge_high_demand(self):
        """High demand / low supply = surge > 1."""
        pricing = DynamicPricing(base_fare=2.0, per_km_rate=1.0, per_min_rate=0.5)
        surge = pricing.get_surge(supply=5, demand=15)
        assert surge == pytest.approx(3.0)


# ── ETAEstimator ──


class TestETAEstimator:
    def test_basic_eta(self):
        """ETA = distance / speed."""
        est = ETAEstimator()
        driver_pos = Position(0, 0)
        pickup_pos = Position(3, 4)  # distance = 5
        eta = est.estimate(driver_pos, pickup_pos, average_speed=5.0)
        assert eta == pytest.approx(1.0)

    def test_traffic_factor(self):
        """Traffic factor increases ETA."""
        est = ETAEstimator()
        driver_pos = Position(0, 0)
        pickup_pos = Position(3, 4)
        eta = est.estimate(driver_pos, pickup_pos, average_speed=5.0, traffic_factor=2.0)
        assert eta == pytest.approx(2.0)

    def test_zero_speed(self):
        """Zero speed returns infinity."""
        est = ETAEstimator()
        eta = est.estimate(Position(0, 0), Position(1, 1), average_speed=0.0)
        assert eta == float('inf')


# ── MetricsCollector ──


class TestMetricsCollector:
    def _make_collector(self):
        mc = MetricsCollector()
        mc.record_tick(TickMetrics(1, 5, 10, 3, 2, 1.5))
        mc.record_tick(TickMetrics(2, 6, 8, 2, 4, 2.0))
        mc.record_tick(TickMetrics(3, 4, 12, 5, 1, 3.0))
        return mc

    def test_record_and_time_series(self):
        """Time series returns (tick, value) pairs."""
        mc = self._make_collector()
        ts = mc.get_time_series("active_drivers")
        assert len(ts) == 3
        assert ts[0] == (1, 5)
        assert ts[1] == (2, 6)

    def test_get_window(self):
        """Window returns subset of ticks."""
        mc = self._make_collector()
        window = mc.get_window(1, 2)
        assert len(window) == 2

    def test_empty_collector(self):
        """Empty collector returns empty time series."""
        mc = MetricsCollector()
        assert mc.get_time_series("active_drivers") == []

    def test_window_out_of_range(self):
        """Window outside data range returns empty."""
        mc = self._make_collector()
        assert mc.get_window(100, 200) == []


# ── KPICalculator ──


class TestKPICalculator:
    def _make_metrics(self):
        return [
            TickMetrics(1, 5, 10, 3, 2, 1.5),
            TickMetrics(2, 6, 8, 2, 4, 2.0),
            TickMetrics(3, 4, 12, 5, 1, 3.0),
        ]

    def test_rider_wait_time(self):
        """Average wait time across ticks."""
        calc = KPICalculator()
        metrics = self._make_metrics()
        avg_wait = calc.rider_wait_time(metrics)
        expected = (1.5 + 2.0 + 3.0) / 3
        assert avg_wait == pytest.approx(expected)

    def test_trips_per_tick(self):
        """Throughput = avg completed trips per tick."""
        calc = KPICalculator()
        metrics = self._make_metrics()
        tpt = calc.trips_per_tick(metrics)
        expected = (2 + 4 + 1) / 3
        assert tpt == pytest.approx(expected)

    def test_supply_demand_ratio(self):
        """Supply/demand ratio averages across ticks with demand."""
        calc = KPICalculator()
        metrics = self._make_metrics()
        ratio = calc.supply_demand_ratio(metrics)
        expected = ((5 / 3) + (6 / 2) + (4 / 5)) / 3
        assert ratio == pytest.approx(expected)

    def test_empty_metrics(self):
        """Empty metrics return zeros."""
        calc = KPICalculator()
        assert calc.rider_wait_time([]) == 0.0
        assert calc.trips_per_tick([]) == 0.0


# ── SimulationReport ──


class TestSimulationReport:
    def _make_report(self):
        mc = MetricsCollector()
        mc.record_tick(TickMetrics(1, 5, 10, 3, 2, 1.5))
        mc.record_tick(TickMetrics(2, 6, 8, 2, 4, 2.0))
        return SimulationReport(mc)

    def test_summary_keys(self):
        """Summary contains expected KPI keys."""
        report = self._make_report()
        summary = report.summary()
        assert "driver_utilization" in summary
        assert "rider_wait_time" in summary
        assert "trips_per_tick" in summary
        assert "total_ticks" in summary

    def test_total_ticks(self):
        """Total ticks matches recorded count."""
        report = self._make_report()
        assert report.summary()["total_ticks"] == 2

    def test_compare(self):
        """Compare returns side-by-side KPIs."""
        r1 = self._make_report()
        mc2 = MetricsCollector()
        mc2.record_tick(TickMetrics(1, 3, 5, 1, 5, 0.5))
        r2 = SimulationReport(mc2)
        comparison = r1.compare(r2)
        assert "rider_wait_time" in comparison
        assert "self" in comparison["rider_wait_time"]
        assert "other" in comparison["rider_wait_time"]


# ── ScenarioComparator ──


class TestScenarioComparator:
    def _make_scenario(self, wait_time: float, trips: int):
        mc = MetricsCollector()
        mc.record_tick(TickMetrics(1, 5, 10, 3, trips, wait_time))
        return SimulationReport(mc)

    def test_compare_all(self):
        """Compare all returns summary for each scenario."""
        comp = ScenarioComparator()
        comp.add_scenario("A", self._make_scenario(1.0, 5))
        comp.add_scenario("B", self._make_scenario(2.0, 3))
        result = comp.compare_all()
        assert "A" in result
        assert "B" in result

    def test_best_by_wait_time(self):
        """Lower wait time scenario is best."""
        comp = ScenarioComparator()
        comp.add_scenario("fast", self._make_scenario(1.0, 5))
        comp.add_scenario("slow", self._make_scenario(3.0, 5))
        assert comp.best_by("rider_wait_time") == "fast"

    def test_best_by_throughput(self):
        """Higher throughput scenario is best."""
        comp = ScenarioComparator()
        comp.add_scenario("high", self._make_scenario(1.0, 10))
        comp.add_scenario("low", self._make_scenario(1.0, 2))
        assert comp.best_by("trips_per_tick") == "high"
