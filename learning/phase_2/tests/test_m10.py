"""Tests for Module 10: Dynamic Pricing."""

import pytest

from learning.phase_2.src.m10_dynamic_pricing.supply_demand import (
    Zone,
    simulate_day,
    demand_curve,
    supply_curve,
)
from learning.phase_2.src.m10_dynamic_pricing.surge import (
    SurgeConfig,
    SurgeModel,
    calculate_surge,
    calculate_fare,
    surge_multiplier_linear,
    surge_multiplier_exponential,
    surge_multiplier_step,
)
from learning.phase_2.src.m10_dynamic_pricing.elasticity import (
    VehicleType,
    ECONOMY,
    STANDARD,
    PREMIUM,
    simulate_price_change,
    simulate_cross_elasticity,
    calculate_demand_after_price_change,
)


class TestSupplyDemand:
    def test_simulate_day_returns_24_snapshots(self):
        zone = Zone(zone_id="z1", name="Test Zone")
        snapshots = simulate_day(zone)
        assert len(snapshots) == 24

    def test_demand_is_positive(self):
        for hour in range(24):
            d = demand_curve(hour, 100.0)
            assert d > 0

    def test_supply_is_positive(self):
        for hour in range(24):
            s = supply_curve(hour, 100.0)
            assert s > 0

    def test_ratio_calculation(self):
        zone = Zone(zone_id="z1", name="Test", base_demand=200, base_supply=100)
        snapshots = simulate_day(zone)
        for snap in snapshots:
            if snap.supply > 0:
                expected = snap.demand / snap.supply
                assert snap.ratio == pytest.approx(expected, abs=0.01)


class TestSurge:
    def test_no_surge_below_threshold(self):
        config = SurgeConfig(surge_threshold=1.2)
        result = calculate_surge(100, 100, config)  # ratio=1.0
        assert result == 1.0

    def test_linear_surge(self):
        config = SurgeConfig(model=SurgeModel.LINEAR, surge_threshold=1.0, linear_k=1.0)
        result = surge_multiplier_linear(2.0, config)
        assert result == pytest.approx(2.0)

    def test_exponential_surge(self):
        config = SurgeConfig(model=SurgeModel.EXPONENTIAL, surge_threshold=1.0, exp_k=0.5)
        result = surge_multiplier_exponential(2.0, config)
        assert result > 1.0

    def test_step_surge(self):
        config = SurgeConfig(model=SurgeModel.STEP)
        result = surge_multiplier_step(1.5, config)
        assert result == 1.50

    def test_max_multiplier_cap(self):
        config = SurgeConfig(model=SurgeModel.LINEAR, max_multiplier=3.0,
                             surge_threshold=1.0, linear_k=10.0)
        result = calculate_surge(1000, 100, config)
        assert result == 3.0

    def test_zero_supply_returns_max(self):
        result = calculate_surge(100, 0)
        assert result == 5.0  # Default max

    def test_calculate_fare_with_surge(self):
        fare = calculate_fare(2.50, 5.0, 15.0, surge=2.0)
        base_fare = (2.50 + 5.0 * 1.50 + 15.0 * 0.30) * 2.0
        assert fare == pytest.approx(round(base_fare, 2))

    def test_minimum_fare(self):
        fare = calculate_fare(0, 0, 0, surge=1.0, minimum_fare=5.00)
        assert fare == 5.00


class TestElasticity:
    def test_negative_elasticity_required(self):
        with pytest.raises(ValueError):
            VehicleType(name="bad", base_demand=100, base_price=10, elasticity=0.5)

    def test_demand_decreases_with_price_increase(self):
        new_demand = calculate_demand_after_price_change(100, -0.8, 50)
        assert new_demand < 100

    def test_elastic_demand_drops_more(self):
        elastic = calculate_demand_after_price_change(100, -1.5, 50)
        inelastic = calculate_demand_after_price_change(100, -0.3, 50)
        assert elastic < inelastic

    def test_economy_loses_revenue_at_high_surge(self):
        resp = simulate_price_change(ECONOMY, surge_multiplier=2.0)
        assert resp.revenue_change_pct < 0  # Revenue drops

    def test_premium_gains_revenue_at_moderate_surge(self):
        resp = simulate_price_change(PREMIUM, surge_multiplier=1.5)
        assert resp.revenue_change_pct > 0  # Revenue increases

    def test_cross_elasticity_increases_substitute_demand(self):
        primary_resp, sub_resp = simulate_cross_elasticity(
            primary=STANDARD, substitute=ECONOMY,
            cross_elasticity=0.5, primary_surge=2.0,
        )
        assert sub_resp.new_demand > sub_resp.original_demand
