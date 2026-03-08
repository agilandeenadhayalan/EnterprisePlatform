"""
Pydantic request/response schemas for the driver location service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --

class LocationUpdateRequest(BaseModel):
    """POST /locations — update driver location."""
    driver_id: str = Field(..., description="Driver UUID")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    heading: Optional[float] = Field(None, ge=0, le=360)
    speed: Optional[float] = Field(None, ge=0)
    accuracy: Optional[float] = Field(None, ge=0)
    source: str = Field("gps", max_length=20)


# -- Response schemas --

class LocationResponse(BaseModel):
    """Location data returned from API."""
    id: str
    driver_id: str
    latitude: float
    longitude: float
    heading: Optional[float] = None
    speed: Optional[float] = None
    accuracy: Optional[float] = None
    source: str
    recorded_at: datetime
    created_at: datetime


class LocationHistoryResponse(BaseModel):
    """GET /drivers/{id}/location/history response."""
    locations: list[LocationResponse]
    total: int
