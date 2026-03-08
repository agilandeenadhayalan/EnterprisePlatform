"""
Price Elasticity Simulator
============================

Models how price changes affect rider demand. Price elasticity is the
percentage change in demand resulting from a 1% change in price.

WHY elasticity matters:
- If demand is elastic (|e| > 1), raising prices REDUCES revenue
- If demand is inelastic (|e| < 1), raising prices INCREASES revenue
- Ride-hailing demand is moderately elastic (|e| ~ 0.5-1.5)
- Different vehicle types have different elasticities

Cross-elasticity:
- When standard rides get expensive, some riders switch to XL or economy
- Cross-elasticity measures how one product's price affects another's demand
- Positive cross-elasticity = substitutes (standard <-> economy)
- Negative cross-elasticity = complements

Real-world data suggests:
- Economy rides: highly elastic (e ~ -1.5, price-sensitive riders)
- Standard rides: moderately elastic (e ~ -0.8)
- Premium rides: inelastic (e ~ -0.3, riders less price-sensitive)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VehicleType:
    """A vehicle type with its own demand characteristics."""
    name: str
    base_demand: float          # Requests per hour at normal price
    base_price: float           # Normal fare for a typical trip
    elasticity: float           # Price elasticity of demand (negative)

    def __post_init__(self) -> None:
        if self.elasticity > 0:
            raise ValueError(
                f"Elasticity should be negative (price up = demand down), "
                f"got {self.elasticity}"
            )


@dataclass
class DemandResponse:
    """Result of a price change on demand."""
    vehicle_type: str
    original_price: float
    new_price: float
    price_change_pct: float
    original_demand: float
    new_demand: float
    demand_change_pct: float
    revenue_before: float
    revenue_after: float
    revenue_change_pct: float


def calculate_demand_after_price_change(
    base_demand: float,
    elasticity: float,
    price_change_pct: float,
) -> float:
    """
    Calculate new demand after a percentage price change.

    Uses the elasticity formula:
        % change in demand = elasticity * % change in price

    Example: If elasticity = -0.8 and price increases 50%:
        demand_change = -0.8 * 50% = -40%
        new_demand = base * (1 - 0.40) = 60% of original

    Returns new demand (floored at 0).
    """
    demand_change_pct = elasticity * price_change_pct
    new_demand = base_demand * (1 + demand_change_pct / 100.0)
    return max(0.0, new_demand)


def simulate_price_change(
    vehicle: VehicleType,
    surge_multiplier: float,
) -> DemandResponse:
    """
    Simulate the effect of a surge multiplier on demand and revenue.

    Returns the demand response including revenue impact.
    """
    new_price = vehicle.base_price * surge_multiplier
    price_change_pct = (surge_multiplier - 1.0) * 100.0

    new_demand = calculate_demand_after_price_change(
        vehicle.base_demand,
        vehicle.elasticity,
        price_change_pct,
    )

    demand_change_pct = ((new_demand - vehicle.base_demand) / vehicle.base_demand * 100.0
                         if vehicle.base_demand > 0 else 0.0)

    revenue_before = vehicle.base_demand * vehicle.base_price
    revenue_after = new_demand * new_price
    revenue_change_pct = ((revenue_after - revenue_before) / revenue_before * 100.0
                          if revenue_before > 0 else 0.0)

    return DemandResponse(
        vehicle_type=vehicle.name,
        original_price=vehicle.base_price,
        new_price=round(new_price, 2),
        price_change_pct=round(price_change_pct, 1),
        original_demand=vehicle.base_demand,
        new_demand=round(new_demand, 1),
        demand_change_pct=round(demand_change_pct, 1),
        revenue_before=round(revenue_before, 2),
        revenue_after=round(revenue_after, 2),
        revenue_change_pct=round(revenue_change_pct, 1),
    )


def simulate_cross_elasticity(
    primary: VehicleType,
    substitute: VehicleType,
    cross_elasticity: float,
    primary_surge: float,
) -> tuple[DemandResponse, DemandResponse]:
    """
    Simulate how a price increase in one vehicle type affects another.

    When standard rides surge, some riders switch to economy.
    Cross-elasticity measures this substitution effect.

    Args:
        primary: Vehicle type with the price change (e.g., standard)
        substitute: Vehicle type affected (e.g., economy)
        cross_elasticity: Cross-price elasticity (positive = substitutes)
        primary_surge: Surge multiplier for the primary vehicle

    Returns:
        Tuple of (primary_response, substitute_response)
    """
    # Direct effect on primary vehicle
    primary_response = simulate_price_change(primary, primary_surge)

    # Cross-effect on substitute vehicle
    primary_price_change_pct = (primary_surge - 1.0) * 100.0
    substitute_demand_change_pct = cross_elasticity * primary_price_change_pct
    new_substitute_demand = substitute.base_demand * (1 + substitute_demand_change_pct / 100.0)
    new_substitute_demand = max(0.0, new_substitute_demand)

    # Substitute keeps its own price (no surge on substitute)
    substitute_revenue_before = substitute.base_demand * substitute.base_price
    substitute_revenue_after = new_substitute_demand * substitute.base_price
    sub_rev_change = ((substitute_revenue_after - substitute_revenue_before)
                      / substitute_revenue_before * 100.0
                      if substitute_revenue_before > 0 else 0.0)

    substitute_response = DemandResponse(
        vehicle_type=substitute.name,
        original_price=substitute.base_price,
        new_price=substitute.base_price,  # No surge on substitute
        price_change_pct=0.0,
        original_demand=substitute.base_demand,
        new_demand=round(new_substitute_demand, 1),
        demand_change_pct=round(substitute_demand_change_pct, 1),
        revenue_before=round(substitute_revenue_before, 2),
        revenue_after=round(substitute_revenue_after, 2),
        revenue_change_pct=round(sub_rev_change, 1),
    )

    return primary_response, substitute_response


# ── Predefined vehicle types ──

ECONOMY = VehicleType(name="economy", base_demand=200, base_price=8.0, elasticity=-1.5)
STANDARD = VehicleType(name="standard", base_demand=150, base_price=15.0, elasticity=-0.8)
PREMIUM = VehicleType(name="premium", base_demand=50, base_price=30.0, elasticity=-0.3)
