"""
Domain models for the region router service.

Manages regions, geo-routing, and latency-based routing.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class RegionStatus(str, Enum):
    """Region operational status."""
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class RoutingStrategy(str, Enum):
    """Routing strategy for selecting target region."""
    GEO = "geo"
    LATENCY = "latency"
    WEIGHTED = "weighted"


class Region:
    """A geographic region with routing metadata."""

    def __init__(
        self,
        id: str,
        name: str,
        code: str,
        endpoint: str,
        status: str = "active",
        is_primary: bool = False,
        latitude: float = 0.0,
        longitude: float = 0.0,
        metadata: Optional[dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.code = code
        self.endpoint = endpoint
        self.status = status
        self.is_primary = is_primary
        self.latitude = latitude
        self.longitude = longitude
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "endpoint": self.endpoint,
            "status": self.status,
            "is_primary": self.is_primary,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class RouteResult:
    """Result of a routing decision."""

    def __init__(
        self,
        region_code: str,
        distance_km: float,
        latency_ms: float,
        score: float,
    ):
        self.region_code = region_code
        self.distance_km = distance_km
        self.latency_ms = latency_ms
        self.score = score

    def to_dict(self) -> dict:
        return {
            "region_code": self.region_code,
            "distance_km": round(self.distance_km, 2),
            "latency_ms": round(self.latency_ms, 2),
            "score": round(self.score, 4),
        }
