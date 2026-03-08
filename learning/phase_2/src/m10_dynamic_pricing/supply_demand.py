"""
Supply/Demand Model
=====================

Simulates driver supply and rider demand throughout a day,
modeling how the demand/supply ratio varies by time and zone.

WHY supply/demand matters:
- When demand > supply, riders wait longer and drivers are overworked
- When supply > demand, drivers sit idle and earn nothing
- Dynamic pricing aims to bring these into equilibrium
- Higher prices reduce demand and attract more supply

Real-world patterns:
- Morning rush (7-9 AM): high demand, moderate supply
- Midday (11 AM-2 PM): moderate demand, moderate supply
- Evening rush (5-7 PM): high demand, moderate supply
- Late night (11 PM-2 AM): low supply, variable demand (events)
- Weekend nights: high demand, low supply
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Zone:
    """A geographic zone for supply/demand tracking."""
    zone_id: str
    name: str
    base_demand: float = 100.0   # Average hourly requests
    base_supply: float = 80.0    # Average available drivers


@dataclass
class SupplyDemandSnapshot:
    """Supply and demand at a specific time in a zone."""
    zone_id: str
    hour: int                    # 0-23
    demand: float                # Rider requests per hour
    supply: float                # Available drivers
    ratio: float                 # demand / supply

    @property
    def is_undersupplied(self) -> bool:
        """Demand exceeds supply — surge pricing territory."""
        return self.ratio > 1.2

    @property
    def is_oversupplied(self) -> bool:
        """Supply exceeds demand — drivers sitting idle."""
        return self.ratio < 0.8


def demand_curve(hour: int, base_demand: float) -> float:
    """
    Model rider demand throughout the day using sinusoidal curves.

    Peaks during morning rush (8 AM) and evening rush (6 PM),
    with a dip overnight (3 AM).
    """
    # Morning peak around 8 AM
    morning = 0.3 * math.sin(math.pi * (hour - 5) / 6) if 5 <= hour <= 11 else 0
    # Evening peak around 6 PM
    evening = 0.4 * math.sin(math.pi * (hour - 15) / 6) if 15 <= hour <= 21 else 0
    # Late night activity (bars closing around 2 AM)
    late_night = 0.2 * math.exp(-((hour - 1) ** 2) / 2) if hour <= 4 or hour >= 22 else 0
    # Base level (never zero)
    base_level = 0.3

    multiplier = base_level + max(0, morning) + max(0, evening) + max(0, late_night)
    return base_demand * multiplier


def supply_curve(hour: int, base_supply: float) -> float:
    """
    Model driver supply throughout the day.

    Drivers prefer daytime hours. Supply drops late at night
    and peaks in the afternoon.
    """
    # Drivers online during daytime
    if 6 <= hour <= 22:
        daytime = 0.5 + 0.3 * math.sin(math.pi * (hour - 6) / 16)
    else:
        daytime = 0.2

    # Weekend night bonus (more drivers for bar crowd)
    late_bonus = 0.15 * math.exp(-((hour - 23) ** 2) / 4) if hour >= 20 else 0

    multiplier = daytime + late_bonus
    return base_supply * multiplier


def simulate_day(
    zone: Zone,
    hours: range | None = None,
) -> list[SupplyDemandSnapshot]:
    """
    Simulate supply and demand for every hour of a day in a zone.

    Returns 24 snapshots (one per hour) showing how the
    demand/supply ratio changes throughout the day.
    """
    if hours is None:
        hours = range(24)

    snapshots: list[SupplyDemandSnapshot] = []
    for hour in hours:
        demand = demand_curve(hour, zone.base_demand)
        supply = supply_curve(hour, zone.base_supply)
        ratio = demand / supply if supply > 0 else float("inf")

        snapshots.append(SupplyDemandSnapshot(
            zone_id=zone.zone_id,
            hour=hour,
            demand=round(demand, 1),
            supply=round(supply, 1),
            ratio=round(ratio, 3),
        ))

    return snapshots
