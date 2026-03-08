"""
Pydantic request/response schemas for the driver availability service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --

class GoOnlineRequest(BaseModel):
    """POST /drivers/{id}/online — go online."""
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class GoOfflineRequest(BaseModel):
    """POST /drivers/{id}/offline — go offline."""
    pass


# -- Response schemas --

class AvailabilityResponse(BaseModel):
    """Driver availability status."""
    id: str
    driver_id: str
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_online_at: Optional[datetime] = None
    last_offline_at: Optional[datetime] = None
    total_online_seconds: int
    created_at: datetime
    updated_at: datetime


class AvailableDriversResponse(BaseModel):
    """GET /available response."""
    drivers: list[AvailabilityResponse]
    total: int
