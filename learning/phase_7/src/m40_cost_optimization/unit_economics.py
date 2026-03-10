"""
Unit economics — calculating per-trip and per-request costs.

WHY THIS MATTERS:
A mobility platform must understand its unit economics: what does it
cost to serve one trip, one API request, one rider? Without this,
you cannot set sustainable pricing, identify cost anomalies, or make
informed build-vs-buy decisions. Unit economics connects infrastructure
costs to business outcomes.

Key concepts:
  - Cost-per-trip: total infrastructure cost / number of trips
  - Contribution margin: revenue minus variable costs per trip
  - Break-even analysis: how many trips to cover fixed costs
  - Cost trending: tracking costs over time to catch drift
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TripCostBreakdown:
    """Breakdown of infrastructure costs for serving trips.

    Separates costs into compute, storage, network, and third-party
    (maps API, payment processing, etc.) to identify which category
    dominates and where optimization efforts should focus.
    """

    compute_cost: float
    storage_cost: float
    network_cost: float
    third_party_cost: float

    @property
    def total(self) -> float:
        """Total cost across all categories."""
        return self.compute_cost + self.storage_cost + self.network_cost + self.third_party_cost


class UnitEconomicsCalculator:
    """Calculate per-unit costs and margins for the platform.

    Converts aggregate infrastructure costs into per-trip and per-request
    metrics that map directly to business unit economics.
    """

    def cost_per_trip(self, total_costs: TripCostBreakdown, num_trips: int) -> float:
        """Calculate all-in cost per trip.

        Simply divides total costs by number of trips. Returns 0.0 if
        num_trips is zero to avoid division errors.
        """
        if num_trips == 0:
            return 0.0
        return total_costs.total / num_trips

    def cost_per_request(self, total_costs: TripCostBreakdown, num_requests: int) -> float:
        """Calculate cost per API request.

        A trip generates multiple API requests (search, match, track,
        payment, etc.), so cost_per_request << cost_per_trip.
        """
        if num_requests == 0:
            return 0.0
        return total_costs.total / num_requests

    def contribution_margin(self, revenue_per_trip: float, cost_per_trip: float) -> float:
        """Calculate contribution margin per trip.

        Contribution margin = (revenue - variable cost) / revenue.
        Returns a fraction (e.g., 0.35 = 35% margin). Returns 0.0 if
        revenue is zero.
        """
        if revenue_per_trip == 0:
            return 0.0
        return (revenue_per_trip - cost_per_trip) / revenue_per_trip

    def break_even_trips(
        self,
        fixed_costs: float,
        revenue_per_trip: float,
        variable_cost_per_trip: float,
    ) -> float:
        """Calculate the number of trips needed to break even.

        Break-even = fixed_costs / (revenue_per_trip - variable_cost_per_trip).
        Returns float('inf') if revenue <= variable cost (never breaks even).
        """
        margin_per_trip = revenue_per_trip - variable_cost_per_trip
        if margin_per_trip <= 0:
            return float('inf')
        return fixed_costs / margin_per_trip


class CostTrend:
    """Track costs over time to detect growth and project future costs.

    Records periodic cost snapshots and computes growth rates to identify
    cost drift before it becomes a problem.
    """

    def __init__(self):
        self._periods: list = []  # list of (date, costs_dict)

    def add_period(self, date: str, costs: dict) -> None:
        """Record costs for a time period.

        Args:
            date: period identifier (e.g., "2024-01")
            costs: dict mapping cost category to amount
        """
        total = sum(costs.values())
        self._periods.append({"date": date, "costs": costs, "total": total})

    def growth_rate(self) -> float:
        """Calculate average monthly cost growth rate.

        Uses simple (last - first) / first / num_periods formula.
        Returns 0.0 if fewer than 2 periods recorded.
        """
        if len(self._periods) < 2:
            return 0.0
        first_total = self._periods[0]["total"]
        last_total = self._periods[-1]["total"]
        if first_total == 0:
            return 0.0
        num_intervals = len(self._periods) - 1
        return (last_total - first_total) / first_total / num_intervals

    def project(self, months: int) -> float:
        """Project costs forward by N months using current growth rate.

        Uses compound growth: last_total * (1 + growth_rate)^months.
        Returns 0.0 if no periods recorded.
        """
        if not self._periods:
            return 0.0
        rate = self.growth_rate()
        last_total = self._periods[-1]["total"]
        return last_total * ((1 + rate) ** months)


class PricingModel:
    """Determine optimal pricing based on cost analysis.

    Calculates minimum viable price (floor) and optimal price considering
    demand elasticity.
    """

    def minimum_price(self, cost_per_trip: float, target_margin: float) -> float:
        """Calculate the floor price to achieve target margin.

        price = cost / (1 - target_margin).
        E.g., cost=$2, margin=0.3 => price = $2 / 0.7 = $2.86.
        Returns cost if margin >= 1.0 (invalid margin).
        """
        if target_margin >= 1.0:
            return cost_per_trip
        return cost_per_trip / (1 - target_margin)

    def optimal_price(self, cost: float, demand_elasticity: float) -> float:
        """Calculate optimal price using markup formula.

        Uses the Lerner index: price = cost * elasticity / (elasticity - 1).
        Only valid for elasticity > 1 (elastic demand). For inelastic
        demand (elasticity <= 1), returns cost * 2 as a default markup.
        """
        if demand_elasticity <= 1.0:
            return cost * 2.0
        return cost * demand_elasticity / (demand_elasticity - 1)
