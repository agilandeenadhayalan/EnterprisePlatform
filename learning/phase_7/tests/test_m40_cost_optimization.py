"""
Tests for M40: Cost Optimization — right-sizing, unit economics, spot instances, cost allocation.
"""

import random
import pytest

from m40_cost_optimization.right_sizing import (
    InstanceMetrics,
    InstanceType,
    UtilizationAnalyzer,
    RightSizer,
    RightSizingReport,
)
from m40_cost_optimization.unit_economics import (
    TripCostBreakdown,
    UnitEconomicsCalculator,
    CostTrend,
    PricingModel,
)
from m40_cost_optimization.spot_instances import (
    SpotPricePoint,
    SpotMarket,
    SpotStrategy,
    SpotInstanceManager,
    FleetComposition,
)
from m40_cost_optimization.cost_allocation import (
    CostTag,
    AllocationRule,
    CostAllocator,
    CostReport,
    ChargebackCalculator,
)


# ── UtilizationAnalyzer ──


class TestUtilizationAnalyzer:
    def test_over_provisioned(self):
        """Low CPU and memory avg => over-provisioned."""
        analyzer = UtilizationAnalyzer()
        metrics = InstanceMetrics(cpu_avg=0.1, cpu_p95=0.2, memory_avg=0.15, memory_p95=0.25, network_io_mbps=10)
        assert analyzer.analyze(metrics) == "over_provisioned"

    def test_under_provisioned(self):
        """High p95 CPU => under-provisioned."""
        analyzer = UtilizationAnalyzer()
        metrics = InstanceMetrics(cpu_avg=0.7, cpu_p95=0.9, memory_avg=0.5, memory_p95=0.6, network_io_mbps=50)
        assert analyzer.analyze(metrics) == "under_provisioned"

    def test_right_sized(self):
        """Moderate utilization => right-sized."""
        analyzer = UtilizationAnalyzer()
        metrics = InstanceMetrics(cpu_avg=0.5, cpu_p95=0.7, memory_avg=0.4, memory_p95=0.6, network_io_mbps=30)
        assert analyzer.analyze(metrics) == "right_sized"

    def test_custom_over_threshold(self):
        """Custom threshold for over-provisioned check."""
        analyzer = UtilizationAnalyzer()
        metrics = InstanceMetrics(cpu_avg=0.15, cpu_p95=0.2, memory_avg=0.18, memory_p95=0.25, network_io_mbps=5)
        assert analyzer.is_over_provisioned(metrics, threshold=0.2)
        assert not analyzer.is_over_provisioned(metrics, threshold=0.1)

    def test_under_provisioned_memory(self):
        """High p95 memory alone triggers under-provisioned."""
        analyzer = UtilizationAnalyzer()
        metrics = InstanceMetrics(cpu_avg=0.3, cpu_p95=0.5, memory_avg=0.6, memory_p95=0.85, network_io_mbps=20)
        assert analyzer.is_under_provisioned(metrics)


# ── RightSizer ──


class TestRightSizer:
    def _make_instances(self):
        return [
            InstanceType("small", 2, 4.0, 0.05),
            InstanceType("medium", 4, 8.0, 0.10),
            InstanceType("large", 8, 16.0, 0.20),
            InstanceType("xlarge", 16, 32.0, 0.40),
        ]

    def test_downsize_recommendation(self):
        """Over-provisioned instance should be downsized."""
        instances = self._make_instances()
        sizer = RightSizer(instances)
        current = InstanceType("xlarge", 16, 32.0, 0.40)
        metrics = InstanceMetrics(cpu_avg=0.1, cpu_p95=0.15, memory_avg=0.1, memory_p95=0.1, network_io_mbps=5)
        rec = sizer.recommend(current, metrics)
        assert rec.cost_per_hour < current.cost_per_hour

    def test_no_downsize_if_right_sized(self):
        """Right-sized instance should keep similar cost."""
        instances = self._make_instances()
        sizer = RightSizer(instances)
        current = InstanceType("medium", 4, 8.0, 0.10)
        metrics = InstanceMetrics(cpu_avg=0.6, cpu_p95=0.65, memory_avg=0.5, memory_p95=0.6, network_io_mbps=20)
        rec = sizer.recommend(current, metrics)
        assert rec.cost_per_hour <= current.cost_per_hour

    def test_savings_calculation(self):
        """Monthly savings computed correctly."""
        instances = self._make_instances()
        sizer = RightSizer(instances)
        current = InstanceType("xlarge", 16, 32.0, 0.40)
        recommended = InstanceType("medium", 4, 8.0, 0.10)
        savings = sizer.calculate_savings(current, recommended)
        expected = (0.40 - 0.10) * 24 * 30
        assert savings == pytest.approx(expected)

    def test_no_savings_if_same(self):
        """No savings when recommending same instance."""
        instances = self._make_instances()
        sizer = RightSizer(instances)
        inst = InstanceType("medium", 4, 8.0, 0.10)
        assert sizer.calculate_savings(inst, inst) == 0.0

    def test_no_savings_if_more_expensive(self):
        """No savings when recommended is more expensive."""
        instances = self._make_instances()
        sizer = RightSizer(instances)
        current = InstanceType("small", 2, 4.0, 0.05)
        recommended = InstanceType("medium", 4, 8.0, 0.10)
        assert sizer.calculate_savings(current, recommended) == 0.0


# ── UnitEconomicsCalculator ──


class TestUnitEconomicsCalculator:
    def test_cost_per_trip(self):
        """Cost per trip divides total by trip count."""
        calc = UnitEconomicsCalculator()
        costs = TripCostBreakdown(10.0, 5.0, 3.0, 2.0)
        assert calc.cost_per_trip(costs, 10) == pytest.approx(2.0)

    def test_cost_per_trip_zero_trips(self):
        """Zero trips returns 0.0."""
        calc = UnitEconomicsCalculator()
        costs = TripCostBreakdown(10.0, 5.0, 3.0, 2.0)
        assert calc.cost_per_trip(costs, 0) == 0.0

    def test_cost_per_request(self):
        """Cost per request divides total by request count."""
        calc = UnitEconomicsCalculator()
        costs = TripCostBreakdown(10.0, 5.0, 3.0, 2.0)
        assert calc.cost_per_request(costs, 100) == pytest.approx(0.2)

    def test_contribution_margin(self):
        """Contribution margin = (revenue - cost) / revenue."""
        calc = UnitEconomicsCalculator()
        margin = calc.contribution_margin(10.0, 7.0)
        assert margin == pytest.approx(0.3)

    def test_contribution_margin_zero_revenue(self):
        """Zero revenue returns 0.0 margin."""
        calc = UnitEconomicsCalculator()
        assert calc.contribution_margin(0.0, 5.0) == 0.0

    def test_break_even_trips(self):
        """Break-even = fixed_costs / margin_per_trip."""
        calc = UnitEconomicsCalculator()
        be = calc.break_even_trips(10000.0, 10.0, 7.0)
        assert be == pytest.approx(10000.0 / 3.0)


# ── CostTrend ──


class TestCostTrend:
    def test_add_and_growth(self):
        """Growth rate calculated from first and last period."""
        trend = CostTrend()
        trend.add_period("2024-01", {"compute": 100})
        trend.add_period("2024-02", {"compute": 110})
        trend.add_period("2024-03", {"compute": 120})
        rate = trend.growth_rate()
        # (120 - 100) / 100 / 2 = 0.1
        assert rate == pytest.approx(0.1)

    def test_single_period_no_growth(self):
        """Single period returns 0.0 growth rate."""
        trend = CostTrend()
        trend.add_period("2024-01", {"compute": 100})
        assert trend.growth_rate() == 0.0

    def test_projection(self):
        """Projection uses compound growth."""
        trend = CostTrend()
        trend.add_period("2024-01", {"compute": 100})
        trend.add_period("2024-02", {"compute": 110})
        proj = trend.project(1)
        rate = trend.growth_rate()
        expected = 110 * (1 + rate)
        assert proj == pytest.approx(expected)

    def test_empty_projection(self):
        """Empty trend projects to 0.0."""
        trend = CostTrend()
        assert trend.project(3) == 0.0


# ── PricingModel ──


class TestPricingModel:
    def test_minimum_price(self):
        """Minimum price = cost / (1 - margin)."""
        model = PricingModel()
        price = model.minimum_price(2.0, 0.3)
        assert price == pytest.approx(2.0 / 0.7)

    def test_minimum_price_high_margin(self):
        """Margin >= 1.0 returns cost as floor."""
        model = PricingModel()
        assert model.minimum_price(2.0, 1.0) == 2.0

    def test_optimal_price_elastic(self):
        """Optimal price with elastic demand."""
        model = PricingModel()
        price = model.optimal_price(2.0, 3.0)
        assert price == pytest.approx(2.0 * 3.0 / 2.0)

    def test_optimal_price_inelastic(self):
        """Inelastic demand returns 2x cost."""
        model = PricingModel()
        assert model.optimal_price(2.0, 0.5) == pytest.approx(4.0)


# ── SpotMarket ──


class TestSpotMarket:
    def test_current_price_range(self):
        """Spot price stays within volatility range."""
        random.seed(42)
        market = SpotMarket(base_price=1.0, volatility=0.2)
        prices = [market.current_price() for _ in range(100)]
        assert all(0.01 <= p <= 1.3 for p in prices)

    def test_price_history_length(self):
        """Price history returns correct number of points."""
        market = SpotMarket(base_price=1.0, volatility=0.1)
        history = market.price_history(24)
        assert len(history) == 24

    def test_spot_price_point_fields(self):
        """SpotPricePoint has expected fields."""
        market = SpotMarket(base_price=0.5, volatility=0.1)
        history = market.price_history(1)
        p = history[0]
        assert p.instance_type == "m5.large"
        assert p.availability_zone == "us-east-1a"

    def test_zero_volatility(self):
        """Zero volatility returns base price exactly."""
        market = SpotMarket(base_price=2.0, volatility=0.0)
        assert market.current_price() == pytest.approx(2.0)


# ── SpotInstanceManager ──


class TestSpotInstanceManager:
    def test_should_bid_balanced(self):
        """Balanced strategy bids at 70% of on-demand."""
        mgr = SpotInstanceManager(on_demand_price=1.0, strategy=SpotStrategy.BALANCED)
        assert mgr.should_bid(0.5)   # 50% < 70%
        assert mgr.should_bid(0.7)   # 70% == 70%
        assert not mgr.should_bid(0.8)  # 80% > 70%

    def test_should_bid_aggressive(self):
        """Aggressive strategy bids at 50% of on-demand."""
        mgr = SpotInstanceManager(on_demand_price=1.0, strategy=SpotStrategy.AGGRESSIVE)
        assert mgr.should_bid(0.4)
        assert not mgr.should_bid(0.6)

    def test_should_bid_conservative(self):
        """Conservative strategy bids at 90% of on-demand."""
        mgr = SpotInstanceManager(on_demand_price=1.0, strategy=SpotStrategy.CONSERVATIVE)
        assert mgr.should_bid(0.85)
        assert not mgr.should_bid(0.95)

    def test_savings_calculation(self):
        """Savings = (on_demand - spot) * hours."""
        mgr = SpotInstanceManager(on_demand_price=1.0)
        savings = mgr.calculate_savings(0.3, 100)
        assert savings == pytest.approx(70.0)

    def test_interruption_probability(self):
        """Lower bids have higher interruption probability."""
        mgr = SpotInstanceManager(on_demand_price=1.0)
        prob_low = mgr.interruption_probability(0.3)
        prob_high = mgr.interruption_probability(0.8)
        assert prob_low > prob_high
        assert mgr.interruption_probability(1.0) == pytest.approx(0.0)


# ── FleetComposition ──


class TestFleetComposition:
    def test_valid_mix(self):
        """Fleet mix summing to 100 is accepted."""
        fleet = FleetComposition()
        fleet.mix(50, 30, 20)
        # Should not raise

    def test_invalid_mix(self):
        """Fleet mix not summing to 100 raises ValueError."""
        fleet = FleetComposition()
        with pytest.raises(ValueError):
            fleet.mix(50, 30, 30)

    def test_blended_cost(self):
        """Blended cost is weighted average."""
        fleet = FleetComposition()
        fleet.mix(50, 30, 20)
        blended = fleet.blended_cost(1.0, 0.3, 0.6)
        expected = (50 * 1.0 + 30 * 0.3 + 20 * 0.6) / 100.0
        assert blended == pytest.approx(expected)

    def test_reliability_score(self):
        """Reliability weighted by instance type."""
        fleet = FleetComposition()
        fleet.mix(60, 20, 20)
        score = fleet.reliability_score()
        expected = (60 * 1.0 + 20 * 1.0 + 20 * 0.5) / 100.0
        assert score == pytest.approx(expected)


# ── CostAllocator ──


class TestCostAllocator:
    def test_proportional_allocation(self):
        """Proportional split by weight."""
        allocator = CostAllocator()
        result = allocator.allocate_proportional(100, {"a": 60, "b": 40})
        assert result["a"] == pytest.approx(60.0)
        assert result["b"] == pytest.approx(40.0)

    def test_proportional_unequal(self):
        """Proportional with unequal weights."""
        allocator = CostAllocator()
        result = allocator.allocate_proportional(300, {"x": 1, "y": 2, "z": 3})
        assert result["x"] == pytest.approx(50.0)
        assert result["z"] == pytest.approx(150.0)

    def test_fixed_allocation(self):
        """Fixed split divides equally."""
        allocator = CostAllocator()
        result = allocator.allocate_fixed(120, ["a", "b", "c"])
        assert result["a"] == pytest.approx(40.0)
        assert result["b"] == pytest.approx(40.0)

    def test_fixed_empty(self):
        """Fixed split with no consumers returns empty."""
        allocator = CostAllocator()
        assert allocator.allocate_fixed(100, []) == {}

    def test_usage_based(self):
        """Usage-based allocation matches proportional logic."""
        allocator = CostAllocator()
        result = allocator.allocate_usage_based(200, {"svc1": 100, "svc2": 300})
        assert result["svc1"] == pytest.approx(50.0)
        assert result["svc2"] == pytest.approx(150.0)

    def test_add_shared_cost(self):
        """Shared costs are stored correctly."""
        allocator = CostAllocator()
        allocator.add_shared_cost("k8s", 500, [CostTag("env", "prod")])
        assert len(allocator._shared_costs) == 1
        assert allocator._shared_costs[0]["amount"] == 500


# ── CostReport ──


class TestCostReport:
    def _make_report(self):
        report = CostReport()
        report.add_allocation("dispatch", "compute", 100, [CostTag("team", "platform")])
        report.add_allocation("dispatch", "storage", 30, [CostTag("team", "platform")])
        report.add_allocation("pricing", "compute", 50, [CostTag("team", "revenue")])
        report.add_allocation("analytics", "storage", 40, [CostTag("team", "data")])
        report.add_allocation("analytics", "compute", 80, [CostTag("team", "data")])
        return report

    def test_by_service(self):
        """Group costs by service name."""
        report = self._make_report()
        by_svc = report.by_service()
        assert by_svc["dispatch"] == pytest.approx(130.0)
        assert by_svc["analytics"] == pytest.approx(120.0)

    def test_by_resource_type(self):
        """Group costs by resource type."""
        report = self._make_report()
        by_res = report.by_resource_type()
        assert by_res["compute"] == pytest.approx(230.0)
        assert by_res["storage"] == pytest.approx(70.0)

    def test_by_tag(self):
        """Group costs by tag value."""
        report = self._make_report()
        by_team = report.by_tag("team")
        assert by_team["platform"] == pytest.approx(130.0)
        assert by_team["data"] == pytest.approx(120.0)

    def test_total(self):
        """Total aggregates all allocations."""
        report = self._make_report()
        assert report.total() == pytest.approx(300.0)

    def test_empty_report(self):
        """Empty report returns zero total."""
        report = CostReport()
        assert report.total() == 0.0


# ── ChargebackCalculator ──


class TestChargebackCalculator:
    def test_chargeback_basic(self):
        """Chargeback maps services to teams."""
        report = CostReport()
        report.add_allocation("dispatch", "compute", 100, [])
        report.add_allocation("pricing", "compute", 50, [])
        calc = ChargebackCalculator()
        result = calc.calculate(report, {"dispatch": "platform", "pricing": "revenue"})
        assert result["platform"] == pytest.approx(100.0)
        assert result["revenue"] == pytest.approx(50.0)

    def test_chargeback_unmapped_service(self):
        """Unmapped services go to 'unassigned'."""
        report = CostReport()
        report.add_allocation("mystery", "compute", 75, [])
        calc = ChargebackCalculator()
        result = calc.calculate(report, {})
        assert result["unassigned"] == pytest.approx(75.0)

    def test_chargeback_multiple_services_one_team(self):
        """Multiple services mapped to the same team aggregate."""
        report = CostReport()
        report.add_allocation("svc_a", "compute", 60, [])
        report.add_allocation("svc_b", "compute", 40, [])
        calc = ChargebackCalculator()
        result = calc.calculate(report, {"svc_a": "eng", "svc_b": "eng"})
        assert result["eng"] == pytest.approx(100.0)

    def test_chargeback_empty_report(self):
        """Empty report produces empty chargeback."""
        report = CostReport()
        calc = ChargebackCalculator()
        result = calc.calculate(report, {})
        assert result == {}
