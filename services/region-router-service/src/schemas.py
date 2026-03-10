"""
Pydantic request/response schemas for the region router API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class RegionCreate(BaseModel):
    """POST /regions — register a new region."""
    name: str = Field(..., description="Region display name")
    code: str = Field(..., description="Unique region code (e.g. us-east-1)")
    endpoint: str = Field(..., description="Region API endpoint URL")
    status: str = Field(default="active", description="Region status: active, degraded, offline")
    is_primary: bool = Field(default=False, description="Whether this is the primary region")
    latitude: float = Field(default=0.0, description="Region latitude")
    longitude: float = Field(default=0.0, description="Region longitude")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional metadata")


class RegionUpdate(BaseModel):
    """PATCH /regions/{code} — update region config."""
    name: Optional[str] = None
    endpoint: Optional[str] = None
    status: Optional[str] = None
    is_primary: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


class RouteRequest(BaseModel):
    """POST /regions/route — route request to optimal region."""
    latitude: float = Field(default=0.0, description="Request origin latitude")
    longitude: float = Field(default=0.0, description="Request origin longitude")
    strategy: str = Field(default="geo", description="Routing strategy: geo, latency, weighted")


# ── Response schemas ──

class RegionResponse(BaseModel):
    """A region."""
    id: str
    name: str
    code: str
    endpoint: str
    status: str
    is_primary: bool
    latitude: float
    longitude: float
    metadata: dict[str, Any] = {}
    created_at: datetime


class RouteResultResponse(BaseModel):
    """A routing result."""
    region_code: str
    distance_km: float
    latency_ms: float
    score: float


class RoutingTableEntry(BaseModel):
    """An entry in the routing table."""
    region_code: str
    endpoint: str
    status: str
    is_primary: bool
    latitude: float
    longitude: float


class LatencyCheckResult(BaseModel):
    """Latency check result for a region."""
    region_code: str
    latency_ms: float
    status: str
