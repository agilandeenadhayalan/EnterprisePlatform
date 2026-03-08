"""
Route service computation layer — Haversine distance calculation.

No database; this module provides pure computation functions.
"""

import math


EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.

    Returns distance in kilometers.
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def estimate_road_distance(straight_line_km: float, road_factor: float = 1.3) -> float:
    """
    Estimate actual road distance from straight-line distance.

    Urban roads are typically 1.2-1.4x the straight-line distance.
    """
    return straight_line_km * road_factor


def estimate_duration_minutes(
    distance_km: float, average_speed_kmh: float = 30.0,
) -> int:
    """
    Estimate trip duration in minutes given distance and average speed.
    """
    if average_speed_kmh <= 0:
        return 0
    hours = distance_km / average_speed_kmh
    return max(1, round(hours * 60))
