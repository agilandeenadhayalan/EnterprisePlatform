"""
Domain models for the emergency service.

SOS alerts and emergency response coordination.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EmergencyType(str, Enum):
    """Emergency types."""
    ACCIDENT = "accident"
    MEDICAL = "medical"
    SECURITY = "security"
    VEHICLE_BREAKDOWN = "vehicle_breakdown"


class AlertStatus(str, Enum):
    """Emergency alert statuses."""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    DISPATCHED = "dispatched"
    RESOLVED = "resolved"


class EmergencyAlert:
    """An emergency alert (SOS)."""

    def __init__(
        self,
        id: str,
        emergency_type: str,
        status: str = "triggered",
        reporter_id: Optional[str] = None,
        location: Optional[dict[str, Any]] = None,
        dispatched_responder: Optional[str] = None,
        created_at: Optional[datetime] = None,
        resolved_at: Optional[datetime] = None,
        description: Optional[str] = None,
    ):
        self.id = id
        self.emergency_type = emergency_type
        self.status = status
        self.reporter_id = reporter_id
        self.location = location or {}
        self.dispatched_responder = dispatched_responder
        self.created_at = created_at or datetime.utcnow()
        self.resolved_at = resolved_at
        self.description = description

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "emergency_type": self.emergency_type,
            "status": self.status,
            "reporter_id": self.reporter_id,
            "location": self.location,
            "dispatched_responder": self.dispatched_responder,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "description": self.description,
        }


class Responder:
    """An emergency responder."""

    def __init__(
        self,
        id: str,
        name: str,
        type: str,
        status: str = "available",
        location: Optional[dict[str, Any]] = None,
    ):
        self.id = id
        self.name = name
        self.type = type
        self.status = status  # available, dispatched
        self.location = location or {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "location": self.location,
        }
