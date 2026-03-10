"""
Pydantic request/response schemas for the emergency API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class SOSRequest(BaseModel):
    """POST /emergency/sos — trigger SOS alert."""
    emergency_type: str = Field(..., description="Emergency type: accident, medical, security, vehicle_breakdown")
    reporter_id: Optional[str] = Field(default=None, description="Reporter identifier")
    location: Optional[dict[str, Any]] = Field(default=None, description="Location data (lat/lng)")
    description: Optional[str] = Field(default=None, description="Emergency description")


class AlertUpdate(BaseModel):
    """PATCH /emergency/alerts/{id} — update alert (acknowledge)."""
    status: Optional[str] = None
    description: Optional[str] = None


class DispatchRequest(BaseModel):
    """POST /emergency/alerts/{id}/dispatch — dispatch responder."""
    responder_id: str = Field(..., description="Responder ID to dispatch")


# ── Response schemas ──

class EmergencyAlertResponse(BaseModel):
    """An emergency alert."""
    id: str
    emergency_type: str
    status: str
    reporter_id: Optional[str] = None
    location: dict[str, Any] = {}
    dispatched_responder: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    description: Optional[str] = None


class ResponderResponse(BaseModel):
    """An emergency responder."""
    id: str
    name: str
    type: str
    status: str
    location: dict[str, Any] = {}
