"""Pydantic schemas for vehicle service."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class CreateVehicleRequest(BaseModel):
    driver_id: Optional[str] = None
    vehicle_type_id: Optional[str] = None
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=2100)
    color: str = Field(..., min_length=1, max_length=50)
    license_plate: str = Field(..., min_length=1, max_length=20)
    vin: Optional[str] = Field(None, max_length=17)
    capacity: int = Field(4, ge=1, le=50)


class UpdateVehicleRequest(BaseModel):
    driver_id: Optional[str] = None
    status: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class VehicleResponse(BaseModel):
    id: str
    driver_id: Optional[str] = None
    vehicle_type_id: Optional[str] = None
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    vin: Optional[str] = None
    status: str
    capacity: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VehicleListResponse(BaseModel):
    vehicles: List[VehicleResponse]
    count: int


class VehicleStatusResponse(BaseModel):
    id: str
    status: str
    is_active: bool
