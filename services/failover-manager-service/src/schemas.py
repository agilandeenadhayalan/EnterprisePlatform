"""
Pydantic request/response schemas for the failover manager API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class FailoverEventCreate(BaseModel):
    """POST /failover/events — record a failover event."""
    source_region: str = Field(..., description="Source region code")
    target_region: str = Field(..., description="Target region code")
    trigger_type: str = Field(default="manual", description="Trigger type: manual, automatic, scheduled")
    reason: str = Field(default="", description="Reason for failover")
    status: str = Field(default="initiated", description="Event status")


class FailoverTrigger(BaseModel):
    """POST /failover/trigger — trigger a failover."""
    source_region: str = Field(..., description="Region to fail over from")
    target_region: str = Field(..., description="Region to fail over to")
    reason: str = Field(default="", description="Reason for triggering failover")


# ── Response schemas ──

class FailoverEventResponse(BaseModel):
    """A failover event."""
    id: str
    source_region: str
    target_region: str
    trigger_type: str
    reason: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None


class RegionHealthResponse(BaseModel):
    """Region health status."""
    region_code: str
    status: str
    consecutive_failures: int
    last_check: datetime


class FailoverStatusResponse(BaseModel):
    """Failover status for a region."""
    region_code: str
    health_status: str
    active_failovers: int
    is_primary: bool
