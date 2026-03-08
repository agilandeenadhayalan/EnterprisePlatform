"""
Nearest Driver Algorithm
=========================

The simplest dispatch strategy: find the closest available driver
to the rider's pickup location using Haversine distance.

WHY Haversine:
- GPS coordinates are on a sphere, not a flat plane
- Euclidean distance gives wrong answers at scale
- Haversine gives the great-circle distance between two points
- Accurate enough for ride-hailing (road distance ~1.3x Haversine)

TRADE-OFFS of nearest-driver:
- [+] Simple and fast (O(n) for n drivers)
- [+] Easy to understand and debug
- [-] Ignores driver rating, acceptance rate, idle time
- [-] Not globally optimal (greedy, local decisions)
- [-] Can starve drivers who are slightly further away
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Calculate the great-circle distance between two GPS points.

    Uses the Haversine formula:
        a = sin^2(dlat/2) + cos(lat1) * cos(lat2) * sin^2(dlon/2)
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        d = R * c

    Returns distance in kilometers.
    """
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


@dataclass
class DriverLocation:
    """A driver's current position and metadata."""
    driver_id: str
    lat: float
    lon: float
    is_available: bool = True
    rating: float = 5.0
    acceptance_rate: float = 0.95
    idle_minutes: float = 0.0
    vehicle_type: str = "standard"


@dataclass
class RideRequest:
    """A rider's pickup request."""
    request_id: str
    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float
    vehicle_type: str = "standard"


@dataclass
class DriverMatch:
    """Result of matching a driver to a request."""
    driver: DriverLocation
    distance_km: float
    estimated_eta_minutes: float  # Rough estimate: distance / avg_speed


def find_nearest_driver(
    request: RideRequest,
    drivers: list[DriverLocation],
) -> DriverMatch | None:
    """
    Find the single nearest available driver to the pickup location.

    Returns None if no available drivers exist.
    """
    available = [d for d in drivers if d.is_available]
    if not available:
        return None

    best: DriverMatch | None = None
    for driver in available:
        dist = haversine_distance(
            request.pickup_lat, request.pickup_lon,
            driver.lat, driver.lon,
        )
        # Rough ETA: assume 30 km/h average city speed
        eta = (dist / 30.0) * 60.0  # minutes

        if best is None or dist < best.distance_km:
            best = DriverMatch(driver=driver, distance_km=dist, estimated_eta_minutes=eta)

    return best


def find_k_nearest_drivers(
    request: RideRequest,
    drivers: list[DriverLocation],
    k: int = 3,
) -> list[DriverMatch]:
    """
    Find the K nearest available drivers to the pickup location.

    WHY K instead of just 1:
    - The nearest driver might decline (low acceptance rate)
    - Sending requests to multiple drivers reduces wait time
    - Allows applying additional scoring before final selection

    Returns up to K matches, sorted by distance (ascending).
    """
    available = [d for d in drivers if d.is_available]

    matches: list[DriverMatch] = []
    for driver in available:
        dist = haversine_distance(
            request.pickup_lat, request.pickup_lon,
            driver.lat, driver.lon,
        )
        eta = (dist / 30.0) * 60.0
        matches.append(DriverMatch(driver=driver, distance_km=dist, estimated_eta_minutes=eta))

    # Sort by distance and return top K
    matches.sort(key=lambda m: m.distance_km)
    return matches[:k]
