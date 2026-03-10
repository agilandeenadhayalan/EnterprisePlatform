"""
Pydantic request/response schemas for the incident API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class IncidentCreate(BaseModel):
    """POST /incidents — report a new incident."""
    type: str = Field(..., description="Incident type (e.g. accident, service_outage)")
    severity: str = Field(..., description="Severity: critical, high, medium, low")
    reported_by: Optional[str] = Field(default=None, description="Reporter identifier")
    description: str = Field(..., description="Incident description")
    location: Optional[dict[str, Any]] = Field(default=None, description="Location data")


class IncidentUpdate(BaseModel):
    """PATCH /incidents/{id} — update an incident."""
    severity: Optional[str] = None
    description: Optional[str] = None
    location: Optional[dict[str, Any]] = None


class NoteCreate(BaseModel):
    """POST /incidents/{id}/notes — add investigation note."""
    author: str = Field(..., description="Note author")
    content: str = Field(..., description="Note content")


class ResolveRequest(BaseModel):
    """POST /incidents/{id}/resolve — resolve an incident."""
    resolution: str = Field(..., description="Resolution description")


# ── Response schemas ──

class IncidentResponse(BaseModel):
    """An incident record."""
    id: str
    type: str
    severity: str
    status: str
    reported_by: Optional[str] = None
    description: str
    location: dict[str, Any] = {}
    investigation_notes: list[dict[str, Any]] = []
    reported_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None


class NoteResponse(BaseModel):
    """An investigation note."""
    author: str
    content: str
    added_at: datetime


class IncidentStatsResponse(BaseModel):
    """Incident statistics."""
    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    avg_resolution_hours: Optional[float] = None
