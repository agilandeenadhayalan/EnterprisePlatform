"""
Haversine Distance & Geospatial Primitives
=============================================

Core geospatial functions: distance between GPS points, bearing
calculation, and point-in-polygon testing.

WHY these primitives:
- Haversine: "How far is this driver from the pickup?"
- Bearing: "Which direction should the driver head?"
- Point-in-polygon: "Is this location inside the surge zone?"

Note: These are pure-Python implementations for learning.
Production systems use PostGIS, H3, or turf.js.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class GeoPoint:
    """A GPS coordinate (latitude, longitude)."""
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not (-90 <= self.lat <= 90):
            raise ValueError(f"Latitude must be [-90, 90], got {self.lat}")
        if not (-180 <= self.lon <= 180):
            raise ValueError(f"Longitude must be [-180, 180], got {self.lon}")


def haversine(p1: GeoPoint, p2: GeoPoint) -> float:
    """
    Great-circle distance between two GPS points in kilometers.

    The Haversine formula accounts for Earth's curvature, giving
    accurate results for any two points on the globe.

    For short distances (< 10 km), the error compared to the
    Vincenty formula is negligible (< 0.1%).
    """
    lat1, lon1 = math.radians(p1.lat), math.radians(p1.lon)
    lat2, lon2 = math.radians(p2.lat), math.radians(p2.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def bearing(p1: GeoPoint, p2: GeoPoint) -> float:
    """
    Calculate the initial bearing (forward azimuth) from p1 to p2.

    Returns bearing in degrees [0, 360) where:
    - 0/360 = North
    - 90 = East
    - 180 = South
    - 270 = West
    """
    lat1, lon1 = math.radians(p1.lat), math.radians(p1.lon)
    lat2, lon2 = math.radians(p2.lat), math.radians(p2.lon)

    dlon = lon2 - lon1

    x = math.sin(dlon) * math.cos(lat2)
    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )

    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def destination_point(
    origin: GeoPoint,
    bearing_deg: float,
    distance_km: float,
) -> GeoPoint:
    """
    Calculate the destination point given a start, bearing, and distance.

    Useful for: "Where will I be if I travel 5km northeast?"
    """
    lat1 = math.radians(origin.lat)
    lon1 = math.radians(origin.lon)
    brng = math.radians(bearing_deg)
    d = distance_km / EARTH_RADIUS_KM  # Angular distance

    lat2 = math.asin(
        math.sin(lat1) * math.cos(d)
        + math.cos(lat1) * math.sin(d) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )

    return GeoPoint(
        lat=round(math.degrees(lat2), 6),
        lon=round(math.degrees(lon2), 6),
    )


def point_in_polygon(point: GeoPoint, polygon: list[GeoPoint]) -> bool:
    """
    Test if a point is inside a polygon using ray casting.

    The ray casting algorithm draws a horizontal ray from the point
    and counts how many polygon edges it crosses. If odd, the point
    is inside; if even, it's outside.

    WHY: "Is this pickup location inside the airport surge zone?"

    Args:
        point: The point to test
        polygon: List of vertices defining the polygon (closed loop not required)
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    j = n - 1

    for i in range(n):
        yi, xi = polygon[i].lat, polygon[i].lon
        yj, xj = polygon[j].lat, polygon[j].lon

        if ((yi > point.lat) != (yj > point.lat)) and (
            point.lon < (xj - xi) * (point.lat - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i

    return inside


def bounding_box(
    center: GeoPoint,
    radius_km: float,
) -> tuple[GeoPoint, GeoPoint]:
    """
    Calculate the bounding box (SW, NE corners) around a center point.

    WHY: Quick spatial filter before expensive distance calculations.
    "Find all drivers within the bounding box, then Haversine-filter."
    """
    # Approximate degrees per km
    lat_delta = radius_km / 111.32  # 1 degree lat ~ 111.32 km
    lon_delta = radius_km / (111.32 * math.cos(math.radians(center.lat)))

    sw = GeoPoint(
        lat=max(-90, center.lat - lat_delta),
        lon=max(-180, center.lon - lon_delta),
    )
    ne = GeoPoint(
        lat=min(90, center.lat + lat_delta),
        lon=min(180, center.lon + lon_delta),
    )

    return sw, ne
