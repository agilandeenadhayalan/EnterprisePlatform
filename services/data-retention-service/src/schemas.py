"""
Pydantic request/response schemas for the data retention API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class RetentionPolicyCreate(BaseModel):
    """POST /retention/policies — create a retention policy."""
    name: str = Field(..., description="Policy name")
    target: str = Field(..., description="Target table or bucket/prefix")
    target_type: str = Field(..., description="Target type: clickhouse or minio")
    retention_days: int = Field(..., gt=0, description="Retention period in days")
    description: Optional[str] = Field(default=None, description="Policy description")
    enabled: bool = Field(default=True, description="Whether policy is active")


class RetentionPolicyUpdate(BaseModel):
    """PATCH /retention/policies/{id} — update a retention policy."""
    name: Optional[str] = None
    target: Optional[str] = None
    target_type: Optional[str] = None
    retention_days: Optional[int] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


# ── Response schemas ──

class RetentionPolicyResponse(BaseModel):
    """A retention policy."""
    id: str
    name: str
    target: str
    target_type: str
    retention_days: int
    description: str = ""
    enabled: bool
    created_at: datetime
    updated_at: datetime


class RetentionRunResponse(BaseModel):
    """A retention enforcement run result."""
    id: str
    policy_id: str
    policy_name: str
    target: str
    records_deleted: int
    bytes_reclaimed: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class RetentionEnforceResponse(BaseModel):
    """Response from running retention enforcement."""
    runs: list[RetentionRunResponse]
    total_policies_checked: int
    total_records_deleted: int
    total_bytes_reclaimed: int


class RetentionStatsResponse(BaseModel):
    """Retention statistics."""
    total_policies: int
    enabled_policies: int
    disabled_policies: int
    total_enforcement_runs: int
    total_records_deleted: int
    total_bytes_reclaimed: int
