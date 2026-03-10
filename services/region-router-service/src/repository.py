"""
Region Router repository — in-memory region and routing storage.

Manages regions and performs geo/latency/weighted routing.
"""

import math
import random
import uuid
from typing import Optional

from models import Region, RouteResult, RoutingStrategy


# Simulated latency table (region_code -> base latency in ms)
SIMULATED_LATENCIES: dict[str, float] = {
    "us-east-1": 15.0,
    "us-west-2": 25.0,
    "eu-west-1": 80.0,
    "ap-southeast-1": 120.0,
    "ap-northeast-1": 110.0,
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lon points using Haversine formula."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class RegionRouterRepository:
    """In-memory region and routing storage."""

    def __init__(self):
        self._regions: dict[str, Region] = {}  # code -> Region

    # ── Region CRUD ──

    def create_region(
        self,
        name: str,
        code: str,
        endpoint: str,
        status: str = "active",
        is_primary: bool = False,
        latitude: float = 0.0,
        longitude: float = 0.0,
        metadata: Optional[dict] = None,
    ) -> Region:
        """Register a new region."""
        region_id = str(uuid.uuid4())
        region = Region(
            id=region_id,
            name=name,
            code=code,
            endpoint=endpoint,
            status=status,
            is_primary=is_primary,
            latitude=latitude,
            longitude=longitude,
            metadata=metadata,
        )
        self._regions[code] = region
        return region

    def get_region(self, code: str) -> Optional[Region]:
        """Get a region by code."""
        return self._regions.get(code)

    def list_regions(self) -> list[Region]:
        """List all regions."""
        return list(self._regions.values())

    def update_region(self, code: str, **fields) -> Optional[Region]:
        """Update specific fields on a region."""
        region = self._regions.get(code)
        if not region:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(region, key):
                setattr(region, key, value)
        return region

    # ── Routing ──

    def route_request(self, latitude: float, longitude: float, strategy: str = "geo") -> Optional[RouteResult]:
        """Route a request to the optimal active region."""
        active_regions = [r for r in self._regions.values() if r.status == "active"]
        if not active_regions:
            return None

        results = []
        for region in active_regions:
            distance = _haversine(latitude, longitude, region.latitude, region.longitude)
            latency = SIMULATED_LATENCIES.get(region.code, 50.0) + random.uniform(0, 5)

            if strategy == RoutingStrategy.GEO:
                score = 1.0 / (1.0 + distance)
            elif strategy == RoutingStrategy.LATENCY:
                score = 1.0 / (1.0 + latency)
            else:  # weighted
                score = 0.6 / (1.0 + distance) + 0.4 / (1.0 + latency)

            results.append(RouteResult(
                region_code=region.code,
                distance_km=distance,
                latency_ms=latency,
                score=score,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[0] if results else None

    def get_routing_table(self) -> list[dict]:
        """Get the current routing table."""
        return [
            {
                "region_code": r.code,
                "endpoint": r.endpoint,
                "status": r.status,
                "is_primary": r.is_primary,
                "latitude": r.latitude,
                "longitude": r.longitude,
            }
            for r in self._regions.values()
        ]

    def check_latencies(self) -> list[dict]:
        """Check latency to all regions."""
        results = []
        for region in self._regions.values():
            base_latency = SIMULATED_LATENCIES.get(region.code, 50.0)
            latency = base_latency + random.uniform(0, 10)
            results.append({
                "region_code": region.code,
                "latency_ms": round(latency, 2),
                "status": region.status,
            })
        return results


# Singleton repository instance
repo = RegionRouterRepository()
