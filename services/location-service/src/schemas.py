"""Pydantic schemas for location service."""

from typing import Optional, List

from pydantic import BaseModel, Field


class GeocodeRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=500)


class GeocodeResponse(BaseModel):
    address: str
    latitude: float
    longitude: float
    confidence: float = Field(..., ge=0, le=1)


class ReverseGeocodeRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ReverseGeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class ZoneResponse(BaseModel):
    zone_id: str
    name: str
    city: str
    bounds: dict  # {north, south, east, west}


class ZoneListResponse(BaseModel):
    zones: List[ZoneResponse]
    count: int
