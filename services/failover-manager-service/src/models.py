"""
Domain models for the failover manager service.

Manages failover events, region health, and promotion.
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class TriggerType(str, Enum):
    """How a failover was triggered."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"


class FailoverStatus(str, Enum):
    """Status of a failover event."""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class HealthStatus(str, Enum):
    """Health status for a region."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    FAILED = "failed"


class FailoverEvent:
    """A failover event record."""

    def __init__(
        self,
        id: str,
        source_region: str,
        target_region: str,
        trigger_type: str = "manual",
        reason: str = "",
        status: str = "initiated",
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.id = id
        self.source_region = source_region
        self.target_region = target_region
        self.trigger_type = trigger_type
        self.reason = reason
        self.status = status
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_region": self.source_region,
            "target_region": self.target_region,
            "trigger_type": self.trigger_type,
            "reason": self.reason,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class RegionHealth:
    """Health status of a region."""

    def __init__(
        self,
        region_code: str,
        status: str = "healthy",
        consecutive_failures: int = 0,
        last_check: Optional[datetime] = None,
    ):
        self.region_code = region_code
        self.status = status
        self.consecutive_failures = consecutive_failures
        self.last_check = last_check or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "region_code": self.region_code,
            "status": self.status,
            "consecutive_failures": self.consecutive_failures,
            "last_check": self.last_check.isoformat(),
        }
