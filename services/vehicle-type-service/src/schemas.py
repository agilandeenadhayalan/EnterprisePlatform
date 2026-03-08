"""Pydantic schemas for vehicle type service."""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class VehicleTypeResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    capacity: int
    luggage_capacity: int
    is_active: bool
    features: Optional[Dict[str, Any]] = None


class VehicleTypeListResponse(BaseModel):
    vehicle_types: List[VehicleTypeResponse]
    count: int


class VehicleTypePricingResponse(BaseModel):
    id: str
    name: str
    display_name: str
    base_fare: float
    per_km_rate: float
    per_minute_rate: float
    minimum_fare: float
    currency: str
