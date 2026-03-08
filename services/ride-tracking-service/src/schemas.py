"""Pydantic schemas for ride tracking service."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class AddWaypointRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None
    speed_kmh: Optional[float] = Field(None, ge=0)
    heading: Optional[float] = Field(None, ge=0, le=360)
    accuracy_meters: Optional[float] = Field(None, ge=0)


class WaypointResponse(BaseModel):
    id: str
    trip_id: str
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None
    accuracy_meters: Optional[float] = None
    sequence_number: int
    recorded_at: Optional[datetime] = None


class TrackResponse(BaseModel):
    trip_id: str
    waypoints: List[WaypointResponse]
    count: int
