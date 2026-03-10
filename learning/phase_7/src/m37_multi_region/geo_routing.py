"""
Geo-Routing — route traffic to the optimal region endpoint.

WHY THIS MATTERS:
Global platforms need to route every request to the best region. "Best" can
mean nearest (lowest physical distance), fastest (lowest measured latency),
or least loaded (best capacity headroom). In practice you use a weighted
combination of all three. Getting this wrong means users experience
unnecessary latency or, worse, get routed to a region that's overloaded
and failing.

Key concepts:
  - Haversine distance: great-circle distance between two lat/lon points.
  - Latency-based routing: use measured RTT, not just distance. A nearby
    region behind a congested link is slower than a farther region with
    a fast path.
  - Weighted routing: composite score combining distance, latency, and load.
  - Latency matrix: measured inter-region latencies for path optimization.
"""

import math
from dataclasses import dataclass, field


@dataclass
class GeoCoordinate:
    """A geographic coordinate (latitude, longitude in degrees)."""
    lat: float
    lon: float

    def distance_to(self, other: "GeoCoordinate") -> float:
        """Great-circle distance in kilometers using the haversine formula.

        Accurate to ~0.5% for most practical distances.
        """
        R = 6371.0  # Earth radius in km

        lat1 = math.radians(self.lat)
        lat2 = math.radians(other.lat)
        dlat = math.radians(other.lat - self.lat)
        dlon = math.radians(other.lon - self.lon)

        a = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


@dataclass
class RegionEndpoint:
    """A region endpoint that can serve traffic.

    Attributes:
        code: unique region identifier (e.g., "us-east-1")
        name: human-readable name
        coordinate: geographic location
        latency_ms: measured latency from a reference point
        status: "active", "draining", or "inactive"
        load_factor: current load as fraction (0.0 = idle, 1.0 = full)
    """
    code: str
    name: str
    coordinate: GeoCoordinate
    latency_ms: float = 0.0
    status: str = "active"
    load_factor: float = 0.0


class GeoRouter:
    """Route traffic to the optimal region based on geography and health.

    Supports three routing strategies:
      - Distance-based: route to the nearest active region
      - Latency-based: route to the lowest-latency active region
      - Weighted: composite score combining multiple factors
    """

    def __init__(self):
        self._regions: dict[str, RegionEndpoint] = {}

    def add_region(self, endpoint: RegionEndpoint) -> None:
        """Register a region endpoint."""
        self._regions[endpoint.code] = endpoint

    def remove_region(self, code: str) -> None:
        """Remove a region endpoint."""
        self._regions.pop(code, None)

    def _active_regions(self) -> list[RegionEndpoint]:
        """Return only active (non-draining, non-inactive) regions."""
        return [r for r in self._regions.values() if r.status == "active"]

    def route_by_distance(self, lat: float, lon: float) -> RegionEndpoint | None:
        """Route to the nearest active region by geographic distance."""
        user_loc = GeoCoordinate(lat, lon)
        active = self._active_regions()
        if not active:
            return None

        return min(active, key=lambda r: user_loc.distance_to(r.coordinate))

    def route_by_latency(self, lat: float, lon: float) -> RegionEndpoint | None:
        """Route to the lowest-latency active region."""
        active = self._active_regions()
        if not active:
            return None

        return min(active, key=lambda r: r.latency_ms)

    def route_weighted(
        self,
        lat: float,
        lon: float,
        distance_weight: float = 0.4,
        latency_weight: float = 0.4,
        load_weight: float = 0.2,
    ) -> RegionEndpoint | None:
        """Route using a weighted composite score.

        Lower score = better region. Each factor is normalized to [0, 1]
        before weighting.

        Args:
            lat, lon: user's geographic coordinates
            distance_weight: weight for geographic distance factor
            latency_weight: weight for measured latency factor
            load_weight: weight for current load factor
        """
        user_loc = GeoCoordinate(lat, lon)
        active = self._active_regions()
        if not active:
            return None

        # Compute raw values
        distances = [user_loc.distance_to(r.coordinate) for r in active]
        latencies = [r.latency_ms for r in active]
        loads = [r.load_factor for r in active]

        # Normalize each factor to [0, 1]
        max_dist = max(distances) if max(distances) > 0 else 1.0
        max_lat = max(latencies) if max(latencies) > 0 else 1.0

        def score(i: int) -> float:
            d_norm = distances[i] / max_dist
            l_norm = latencies[i] / max_lat
            return (distance_weight * d_norm
                    + latency_weight * l_norm
                    + load_weight * loads[i])

        best_idx = min(range(len(active)), key=score)
        return active[best_idx]


class LatencyMatrix:
    """Measured inter-region latencies for path optimization.

    Maintains a matrix of region-to-region latencies updated by periodic
    health checks. Used to find the best path from any source region.
    """

    def __init__(self):
        self._latencies: dict[str, dict[str, float]] = {}

    def update(self, from_region: str, to_region: str, latency_ms: float) -> None:
        """Record measured latency between two regions."""
        if from_region not in self._latencies:
            self._latencies[from_region] = {}
        self._latencies[from_region][to_region] = latency_ms

    def get_latency(self, from_region: str, to_region: str) -> float | None:
        """Get recorded latency between two regions."""
        return self._latencies.get(from_region, {}).get(to_region)

    def get_best_path(self, from_region: str) -> str | None:
        """Return the region with the lowest latency from the source.

        Simple direct-path optimization — returns the neighbor with
        the lowest measured latency.
        """
        paths = self._latencies.get(from_region, {})
        if not paths:
            return None
        return min(paths, key=paths.get)

    def get_all_from(self, from_region: str) -> dict[str, float]:
        """Return all measured latencies from a source region."""
        return dict(self._latencies.get(from_region, {}))
