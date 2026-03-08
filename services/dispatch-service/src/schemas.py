"""
Pydantic request/response schemas for the dispatch service API.

Defines shapes for dispatch assignment requests, driver scoring,
and zone management.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class DispatchRequest(BaseModel):
    """POST /dispatch — assign a driver to a trip."""
    trip_id: str = Field(..., description="Trip UUID to assign a driver to")
    driver_id: str = Field(..., description="Driver UUID to assign")
    distance_to_pickup: Optional[float] = Field(None, ge=0, description="Distance in miles to pickup")
    driver_rating: Optional[float] = Field(None, ge=0, le=5, description="Driver rating (0-5)")
    acceptance_rate: Optional[float] = Field(None, ge=0, le=1, description="Driver acceptance rate (0-1)")
    cancellation_rate: Optional[float] = Field(None, ge=0, le=1, description="Driver cancellation rate (0-1)")


# ── Response schemas ──

class DispatchAssignmentResponse(BaseModel):
    """Single dispatch assignment."""
    id: str
    trip_id: str
    driver_id: str
    status: str
    score: float
    distance_to_pickup: Optional[float] = None
    assigned_at: datetime
    responded_at: Optional[datetime] = None
    created_at: datetime


class DispatchStatusResponse(BaseModel):
    """GET /dispatch/{id}/status — assignment status."""
    id: str
    status: str
    score: float
    assigned_at: datetime
    responded_at: Optional[datetime] = None


class TripAssignmentsResponse(BaseModel):
    """GET /trips/{id}/assignments — all assignments for a trip."""
    trip_id: str
    assignments: list[DispatchAssignmentResponse]
    count: int


class DispatchZoneResponse(BaseModel):
    """Single dispatch zone."""
    id: str
    name: str
    city: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    is_active: bool
    created_at: datetime


class ZoneListResponse(BaseModel):
    """GET /zones — all dispatch zones."""
    zones: list[DispatchZoneResponse]
    count: int
