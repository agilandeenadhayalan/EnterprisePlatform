"""
Domain models for the safety service.

Driver and rider safety scoring and alert management.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EntityType(str, Enum):
    """Entity types for safety scoring."""
    DRIVER = "driver"
    RIDER = "rider"


class SafetyScore:
    """A safety score for a driver or rider."""

    def __init__(
        self,
        id: str,
        entity_type: str,
        entity_id: str,
        score: float,
        factors: Optional[dict[str, Any]] = None,
        calculated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.score = score
        self.factors = factors or {}
        self.calculated_at = calculated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "score": self.score,
            "factors": self.factors,
            "calculated_at": self.calculated_at.isoformat(),
        }


class SafetyAlert:
    """A safety alert for a driver or rider."""

    def __init__(
        self,
        id: str,
        entity_type: str,
        entity_id: str,
        alert_type: str,
        severity: str,
        message: str,
        status: str = "open",
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.status = status
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
