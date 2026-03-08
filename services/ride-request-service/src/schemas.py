"""
Pydantic schemas for the ride request service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateRideRequestRequest(BaseModel):
    rider_id: str
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    pickup_address: Optional[str] = None
    dropoff_latitude: float = Field(..., ge=-90, le=90)
    dropoff_longitude: float = Field(..., ge=-180, le=180)
    dropoff_address: Optional[str] = None
    vehicle_type: Optional[str] = None


class RideRequestResponse(BaseModel):
    id: str
    rider_id: str
    status: str
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: Optional[str] = None
    dropoff_latitude: float
    dropoff_longitude: float
    dropoff_address: Optional[str] = None
    vehicle_type: Optional[str] = None
    estimated_fare: Optional[float] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class RideRequestStatusResponse(BaseModel):
    id: str
    status: str
    updated_at: Optional[datetime] = None
