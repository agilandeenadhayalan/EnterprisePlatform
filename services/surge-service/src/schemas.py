"""
Pydantic request/response schemas for the surge service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class SurgeUpdateRequest(BaseModel):
    """PUT /surge/{zone_id} — update surge multiplier."""
    surge_multiplier: float = Field(..., ge=1.0, le=10.0, description="Surge multiplier (1.0-10.0)")
    demand_count: Optional[int] = Field(None, ge=0)
    supply_count: Optional[int] = Field(None, ge=0)


class SurgeCalculateRequest(BaseModel):
    """POST /surge/calculate — calculate surge from supply/demand."""
    zone_id: str
    demand_count: int = Field(..., ge=0)
    supply_count: int = Field(..., ge=0)


# ── Response schemas ──

class SurgeZoneResponse(BaseModel):
    """Single surge zone."""
    id: str
    zone_id: str
    zone_name: str
    surge_multiplier: float
    demand_count: int
    supply_count: int
    is_active: bool
    last_calculated_at: Optional[datetime] = None
    created_at: datetime


class SurgeActiveListResponse(BaseModel):
    """GET /surge/active — zones with active surge."""
    zones: list[SurgeZoneResponse]
    count: int


class SurgeCalculateResponse(BaseModel):
    """POST /surge/calculate — calculated surge result."""
    zone_id: str
    demand_count: int
    supply_count: int
    calculated_multiplier: float
