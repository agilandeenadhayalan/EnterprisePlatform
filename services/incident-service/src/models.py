"""
Domain models for the incident service.

Incident lifecycle management — reporting, investigation, resolution.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(str, Enum):
    """Incident lifecycle statuses."""
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Incident:
    """An incident record."""

    def __init__(
        self,
        id: str,
        type: str,
        severity: str,
        status: str = "reported",
        reported_by: Optional[str] = None,
        description: str = "",
        location: Optional[dict[str, Any]] = None,
        investigation_notes: Optional[list[dict[str, Any]]] = None,
        reported_at: Optional[datetime] = None,
        resolved_at: Optional[datetime] = None,
        resolution: Optional[str] = None,
    ):
        self.id = id
        self.type = type
        self.severity = severity
        self.status = status
        self.reported_by = reported_by
        self.description = description
        self.location = location or {}
        self.investigation_notes = investigation_notes or []
        self.reported_at = reported_at or datetime.utcnow()
        self.resolved_at = resolved_at
        self.resolution = resolution

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "severity": self.severity,
            "status": self.status,
            "reported_by": self.reported_by,
            "description": self.description,
            "location": self.location,
            "investigation_notes": self.investigation_notes,
            "reported_at": self.reported_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
        }
