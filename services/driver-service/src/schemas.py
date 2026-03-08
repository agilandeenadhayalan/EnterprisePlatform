"""
Pydantic request/response schemas for the driver service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --

class DriverCreateRequest(BaseModel):
    """POST /drivers — register a new driver."""
    user_id: str = Field(..., description="Associated user account ID")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., description="Driver's email address")
    phone: str = Field(..., max_length=20)
    license_number: str = Field(..., max_length=50)
    vehicle_type: str = Field("sedan", max_length=30)
    vehicle_make: Optional[str] = Field(None, max_length=50)
    vehicle_model: Optional[str] = Field(None, max_length=50)
    vehicle_year: Optional[int] = None
    vehicle_plate: Optional[str] = Field(None, max_length=20)


class DriverUpdateRequest(BaseModel):
    """PATCH /drivers/{id} — update driver info."""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    vehicle_type: Optional[str] = Field(None, max_length=30)
    vehicle_make: Optional[str] = Field(None, max_length=50)
    vehicle_model: Optional[str] = Field(None, max_length=50)
    vehicle_year: Optional[int] = None
    vehicle_plate: Optional[str] = Field(None, max_length=20)


class NearbyQueryParams(BaseModel):
    """GET /drivers/nearby query params."""
    latitude: float
    longitude: float
    radius_km: float = Field(5.0, gt=0, le=50)
    limit: int = Field(10, gt=0, le=100)


# -- Response schemas --

class DriverResponse(BaseModel):
    """Driver data returned from API."""
    id: str
    user_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    license_number: str
    vehicle_type: str
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_plate: Optional[str] = None
    rating: float
    total_trips: int
    acceptance_rate: float
    is_active: bool
    is_verified: bool
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class DriverListResponse(BaseModel):
    """GET /drivers response with list."""
    drivers: list[DriverResponse]
    total: int
