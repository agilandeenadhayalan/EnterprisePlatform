"""
Spot instance management — leveraging preemptible compute for savings.

WHY THIS MATTERS:
Spot/preemptible instances cost 60-90% less than on-demand but can be
reclaimed with short notice. For a mobility platform, batch processing
(trip analytics, ML training, map tile generation) is ideal for spot.
Real-time dispatch should stay on-demand/reserved. A well-designed fleet
mixes instance types to balance cost and reliability.

Key concepts:
  - Spot pricing: fluctuates based on supply/demand in each AZ
  - Bidding strategy: aggressive (lower bid, more interruptions) vs
    conservative (higher bid, fewer interruptions)
  - Fleet composition: blending on-demand, spot, and reserved instances
  - Interruption handling: graceful degradation when spots are reclaimed
"""

import random
from dataclasses import dataclass
from enum import Enum


@dataclass
class SpotPricePoint:
    """A single spot price observation.

    Represents the spot price for a specific instance type in a
    specific availability zone at a point in time.
    """

    timestamp: float
    price: float
    instance_type: str
    availability_zone: str


class SpotMarket:
    """Simulated spot instance market with price fluctuations.

    Models spot pricing as a base price with random volatility.
    Real spot markets are more complex (driven by regional supply/demand),
    but this captures the essential dynamics for strategy testing.
    """

    def __init__(self, base_price: float, volatility: float = 0.2):
        """Initialize the spot market simulator.

        Args:
            base_price: the mean spot price
            volatility: fraction of base_price for random fluctuation (0.0 - 1.0)
        """
        self._base_price = base_price
        self._volatility = volatility

    def current_price(self) -> float:
        """Get the current spot price with random fluctuation.

        Price = base * (1 + uniform(-volatility, +volatility)).
        Clamped to a minimum of 0.01 to avoid negative prices.
        """
        fluctuation = random.uniform(-self._volatility, self._volatility)
        price = self._base_price * (1 + fluctuation)
        return max(0.01, price)

    def price_history(self, hours: int) -> list:
        """Generate a synthetic price history.

        Returns a list of SpotPricePoint for the last N hours,
        one observation per hour.
        """
        history = []
        for h in range(hours):
            price = self.current_price()
            history.append(SpotPricePoint(
                timestamp=float(h),
                price=price,
                instance_type="m5.large",
                availability_zone="us-east-1a",
            ))
        return history


class SpotStrategy(Enum):
    """Bidding strategy for spot instances.

    Aggressive: bid at 50% of on-demand (high savings, high interruption risk).
    Balanced: bid at 70% of on-demand (moderate savings, moderate risk).
    Conservative: bid at 90% of on-demand (lower savings, low risk).
    """

    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class SpotInstanceManager:
    """Manage spot instance bidding and cost analysis.

    Decides whether to bid on spot instances based on the current
    price and the chosen strategy, and calculates savings compared
    to on-demand pricing.
    """

    def __init__(self, on_demand_price: float, strategy: SpotStrategy = SpotStrategy.BALANCED):
        self._on_demand_price = on_demand_price
        self._strategy = strategy
        self._bid_thresholds = {
            SpotStrategy.AGGRESSIVE: 0.5,
            SpotStrategy.BALANCED: 0.7,
            SpotStrategy.CONSERVATIVE: 0.9,
        }

    def should_bid(self, spot_price: float) -> bool:
        """Decide if the spot price is acceptable for this strategy.

        Returns True if spot_price <= on_demand_price * threshold.
        """
        threshold = self._bid_thresholds[self._strategy]
        max_acceptable = self._on_demand_price * threshold
        return spot_price <= max_acceptable

    def calculate_savings(self, spot_price: float, hours: int) -> float:
        """Calculate savings vs on-demand for a given duration.

        savings = (on_demand - spot) * hours.
        Returns 0.0 if spot is more expensive.
        """
        delta = self._on_demand_price - spot_price
        if delta <= 0:
            return 0.0
        return delta * hours

    def interruption_probability(self, bid_price: float) -> float:
        """Estimate interruption probability based on bid price.

        Lower bids relative to on-demand have higher interruption risk.
        probability = 1 - (bid_price / on_demand_price), clamped to [0, 1].
        A bid equal to on-demand has ~0% interruption; a bid at $0 has ~100%.
        """
        if self._on_demand_price == 0:
            return 1.0
        ratio = bid_price / self._on_demand_price
        return max(0.0, min(1.0, 1.0 - ratio))


class FleetComposition:
    """Define and analyze a mixed-instance fleet.

    Combines on-demand, spot, and reserved instances to balance
    cost savings with reliability guarantees.
    """

    def __init__(self):
        self._on_demand_pct: float = 0.0
        self._spot_pct: float = 0.0
        self._reserved_pct: float = 0.0

    def mix(self, on_demand_pct: float, spot_pct: float, reserved_pct: float) -> None:
        """Set the fleet composition percentages.

        Validates that percentages sum to 100. Raises ValueError if not.
        """
        total = on_demand_pct + spot_pct + reserved_pct
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Percentages must sum to 100, got {total}")
        self._on_demand_pct = on_demand_pct
        self._spot_pct = spot_pct
        self._reserved_pct = reserved_pct

    def blended_cost(
        self,
        od_price: float,
        spot_price: float,
        reserved_price: float,
    ) -> float:
        """Calculate the weighted average hourly cost.

        blended = (od% * od_price + spot% * spot_price + reserved% * reserved_price) / 100.
        """
        return (
            self._on_demand_pct * od_price
            + self._spot_pct * spot_price
            + self._reserved_pct * reserved_price
        ) / 100.0

    def reliability_score(self) -> float:
        """Calculate fleet reliability score (0.0 - 1.0).

        On-demand and reserved are fully reliable (weight 1.0).
        Spot instances are partially reliable (weight 0.5).
        Score = (od% * 1.0 + reserved% * 1.0 + spot% * 0.5) / 100.
        """
        reliable = self._on_demand_pct * 1.0 + self._reserved_pct * 1.0
        partial = self._spot_pct * 0.5
        return (reliable + partial) / 100.0
