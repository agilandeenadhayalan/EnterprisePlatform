"""Pydantic schemas for the toll service API."""
from typing import Optional
from pydantic import BaseModel, Field

class TollEstimateRequest(BaseModel):
    """GET /tolls/estimate query params converted to body for POST."""
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lon: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lon: float = Field(..., ge=-180, le=180)
    vehicle_type: str = Field(default="car")

class TollCalculateRequest(BaseModel):
    """POST /tolls/calculate — calculate tolls for a route."""
    route_points: list[dict] = Field(..., min_length=2, description="List of {lat, lon} points along the route")
    vehicle_type: str = Field(default="car")

class TollSegment(BaseModel):
    name: str
    cost: float
    lat: float
    lon: float

class TollEstimateResponse(BaseModel):
    estimated_toll: float
    currency: str = "USD"
    toll_segments: list[TollSegment] = []
    confidence: float

class TollCalculateResponse(BaseModel):
    total_toll: float
    currency: str = "USD"
    toll_segments: list[TollSegment]
    route_has_tolls: bool
