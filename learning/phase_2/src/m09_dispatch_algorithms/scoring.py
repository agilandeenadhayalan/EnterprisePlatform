"""
Weighted Scoring Model
========================

Multi-factor scoring that goes beyond simple distance to rank drivers.
Each factor is normalized to 0-1 and combined with configurable weights.

WHY weighted scoring over nearest-driver:
- Distance alone ignores quality factors
- High-rated drivers give better experiences
- Drivers with high acceptance rates are more reliable
- Idle drivers should be prioritized (fairness)

Score formula:
    score = w1*distance_score + w2*rating_score + w3*acceptance_score + w4*idle_time_score

All factors normalized to [0, 1] where 1 = best.
"""

from __future__ import annotations

from dataclasses import dataclass
from .nearest_driver import (
    DriverLocation,
    RideRequest,
    haversine_distance,
)


@dataclass
class ScoringWeights:
    """
    Configurable weights for the scoring model.

    Weights should sum to 1.0 for interpretability,
    but the algorithm works with any positive weights.
    """
    distance: float = 0.40    # Closest driver
    rating: float = 0.25      # Best rated driver
    acceptance: float = 0.20  # Most reliable driver
    idle_time: float = 0.15   # Fairness: longest waiting driver

    def __post_init__(self) -> None:
        total = self.distance + self.rating + self.acceptance + self.idle_time
        if total <= 0:
            raise ValueError("Weights must sum to a positive number")


@dataclass
class ScoredDriver:
    """A driver with their composite score and factor breakdown."""
    driver: DriverLocation
    total_score: float
    distance_score: float
    rating_score: float
    acceptance_score: float
    idle_time_score: float
    distance_km: float


def normalize_distance(distance_km: float, max_distance_km: float = 10.0) -> float:
    """
    Normalize distance to [0, 1] where 1 = closest.

    Invert because closer is better. Clamp at max_distance.
    """
    if max_distance_km <= 0:
        return 0.0
    clamped = min(distance_km, max_distance_km)
    return 1.0 - (clamped / max_distance_km)


def normalize_rating(rating: float, min_rating: float = 1.0, max_rating: float = 5.0) -> float:
    """Normalize rating to [0, 1] where 1 = highest rating."""
    if max_rating <= min_rating:
        return 0.0
    return (rating - min_rating) / (max_rating - min_rating)


def normalize_acceptance(rate: float) -> float:
    """Acceptance rate is already 0-1, just clamp it."""
    return max(0.0, min(1.0, rate))


def normalize_idle_time(idle_minutes: float, max_idle_minutes: float = 60.0) -> float:
    """
    Normalize idle time to [0, 1] where 1 = longest idle.

    Prioritizing idle drivers improves fairness — prevents
    some drivers from getting all the requests.
    """
    if max_idle_minutes <= 0:
        return 0.0
    clamped = min(idle_minutes, max_idle_minutes)
    return clamped / max_idle_minutes


def score_drivers(
    request: RideRequest,
    drivers: list[DriverLocation],
    weights: ScoringWeights | None = None,
    max_distance_km: float = 10.0,
) -> list[ScoredDriver]:
    """
    Score and rank all available drivers using the weighted model.

    Returns drivers sorted by score (highest first).
    Only includes available drivers within max_distance_km.
    """
    if weights is None:
        weights = ScoringWeights()

    available = [d for d in drivers if d.is_available]
    scored: list[ScoredDriver] = []

    for driver in available:
        dist = haversine_distance(
            request.pickup_lat, request.pickup_lon,
            driver.lat, driver.lon,
        )

        # Skip drivers beyond max distance
        if dist > max_distance_km:
            continue

        d_score = normalize_distance(dist, max_distance_km)
        r_score = normalize_rating(driver.rating)
        a_score = normalize_acceptance(driver.acceptance_rate)
        i_score = normalize_idle_time(driver.idle_minutes)

        total = (
            weights.distance * d_score
            + weights.rating * r_score
            + weights.acceptance * a_score
            + weights.idle_time * i_score
        )

        scored.append(ScoredDriver(
            driver=driver,
            total_score=round(total, 4),
            distance_score=round(d_score, 4),
            rating_score=round(r_score, 4),
            acceptance_score=round(a_score, 4),
            idle_time_score=round(i_score, 4),
            distance_km=round(dist, 4),
        ))

    # Sort by total score descending (highest = best match)
    scored.sort(key=lambda s: s.total_score, reverse=True)
    return scored
