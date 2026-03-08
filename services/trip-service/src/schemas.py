"""
Pydantic request/response schemas for the trip service API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Request schemas ──

class CreateTripRequest(BaseModel):
    """POST /trips — create a new trip."""
    rider_id: str = Field(..., description="UUID of the rider")
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    pickup_address: Optional[str] = None
    dropoff_latitude: float = Field(..., ge=-90, le=90)
    dropoff_longitude: float = Field(..., ge=-180, le=180)
    dropoff_address: Optional[str] = None
    vehicle_type: Optional[str] = None


class UpdateTripStatusRequest(BaseModel):
    """PATCH /trips/{id}/status — update trip status."""
    status: str = Field(..., description="New trip status")
    driver_id: Optional[str] = None
    vehicle_id: Optional[str] = None


# ── Response schemas ──

class TripResponse(BaseModel):
    """Single trip response."""
    id: str
    rider_id: str
    driver_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    status: str
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: Optional[str] = None
    dropoff_latitude: float
    dropoff_longitude: float
    dropoff_address: Optional[str] = None
    estimated_distance_km: Optional[float] = None
    actual_distance_km: Optional[float] = None
    estimated_duration_minutes: Optional[int] = None
    actual_duration_minutes: Optional[int] = None
    fare_amount: Optional[float] = None
    currency: str = "USD"
    vehicle_type: Optional[str] = None
    requested_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class TripListResponse(BaseModel):
    """GET /trips — list response."""
    trips: List[TripResponse]
    count: int
