"""
Driver matching service — scoring and matching logic.

No database access — all matching is computed in memory.
This module acts as the 'repository' layer but performs
pure computation instead of DB operations.
"""

import math
from typing import Optional

import schemas
import config as service_config


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the Haversine distance between two points in kilometers.

    The Haversine formula accounts for Earth's curvature, providing accurate
    results for short to medium distances.
    """
    R = 6371.0  # Earth radius in km
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def compute_score(
    distance_km: float,
    rating: float,
    acceptance_rate: float,
    max_distance_km: float = 10.0,
) -> float:
    """
    Compute a match score for a driver candidate.

    Score components (0-1 each, weighted):
    - Distance: closer is better (inverse of distance / max_distance)
    - Rating: higher is better (rating / 5.0)
    - Acceptance rate: higher is better (direct value)

    Returns a score between 0.0 and 1.0 (higher = better match).
    """
    settings = service_config.settings

    # Normalize distance (0 = at max distance, 1 = right here)
    distance_score = max(0.0, 1.0 - (distance_km / max_distance_km))

    # Normalize rating (0-5 → 0-1)
    rating_score = min(rating / 5.0, 1.0)

    # Acceptance rate is already 0-1
    acceptance_score = min(acceptance_rate, 1.0)

    # Weighted combination
    score = (
        settings.distance_weight * distance_score +
        settings.rating_weight * rating_score +
        settings.acceptance_rate_weight * acceptance_score
    )

    return round(score, 4)


def match_drivers(request: schemas.MatchRequest) -> schemas.MatchResponse:
    """
    Score and rank driver candidates for a trip.

    Steps:
    1. Calculate distance from each candidate to pickup location
    2. Filter out candidates beyond max_distance_km
    3. Optionally filter by vehicle type preference
    4. Score each eligible candidate
    5. Rank by score (descending)
    """
    scored: list[schemas.ScoredCandidate] = []

    for candidate in request.candidates:
        distance = haversine_distance(
            request.pickup_latitude, request.pickup_longitude,
            candidate.latitude, candidate.longitude,
        )

        # Skip if too far
        if distance > request.max_distance_km:
            continue

        # Skip if vehicle type doesn't match preference
        if request.vehicle_type_preference and candidate.vehicle_type != request.vehicle_type_preference:
            continue

        score = compute_score(
            distance_km=distance,
            rating=candidate.rating,
            acceptance_rate=candidate.acceptance_rate,
            max_distance_km=request.max_distance_km,
        )

        scored.append(schemas.ScoredCandidate(
            driver_id=candidate.driver_id,
            distance_km=round(distance, 2),
            rating=candidate.rating,
            acceptance_rate=candidate.acceptance_rate,
            total_trips=candidate.total_trips,
            vehicle_type=candidate.vehicle_type,
            score=score,
            rank=0,  # Set after sorting
        ))

    # Sort by score descending
    scored.sort(key=lambda c: c.score, reverse=True)

    # Assign ranks
    for i, candidate in enumerate(scored, start=1):
        candidate.rank = i

    return schemas.MatchResponse(
        trip_id=request.trip_id,
        best_match=scored[0] if scored else None,
        candidates=scored,
        total_candidates=len(request.candidates),
        total_eligible=len(scored),
    )


# In-memory cache for recent match results (for GET /candidates/{trip_id})
_match_cache: dict[str, schemas.MatchResponse] = {}


def cache_match_result(trip_id: str, result: schemas.MatchResponse) -> None:
    """Cache a match result for later retrieval."""
    _match_cache[trip_id] = result
    # Keep cache bounded
    if len(_match_cache) > 1000:
        oldest = next(iter(_match_cache))
        del _match_cache[oldest]


def get_cached_result(trip_id: str) -> Optional[schemas.MatchResponse]:
    """Retrieve a cached match result."""
    return _match_cache.get(trip_id)
