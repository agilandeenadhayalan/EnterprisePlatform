"""
Pydantic request/response schemas for the conflict resolver API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class DetectRequest(BaseModel):
    """POST /conflicts/detect — detect conflicts between two versions."""
    entity_id: str = Field(..., description="Entity being compared")
    version_a: dict[str, Any] = Field(..., description="First version with timestamp")
    version_b: dict[str, Any] = Field(..., description="Second version with timestamp")


class ResolveRequest(BaseModel):
    """POST /conflicts/resolve — resolve a conflict."""
    conflict_id: str = Field(..., description="Conflict ID to resolve")
    strategy: str = Field(..., description="Resolution strategy: lww, merge, manual, crdt")
    manual_value: Optional[Any] = Field(default=None, description="Manual resolution value")


class MergeRequest(BaseModel):
    """POST /conflicts/merge — CRDT merge operation."""
    merge_type: str = Field(..., description="Merge type: counter, set, register")
    state_a: Any = Field(..., description="First state")
    state_b: Any = Field(..., description="Second state")


# ── Response schemas ──

class ConflictResponse(BaseModel):
    """A conflict record."""
    id: str
    conflict_type: str
    entity_id: str
    version_a: dict[str, Any]
    version_b: dict[str, Any]
    resolution_strategy: Optional[str] = None
    resolved_value: Optional[Any] = None
    status: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None


class MergeResultResponse(BaseModel):
    """Result of a CRDT merge."""
    merged_state: Any
    merge_type: str
    elements_merged: int


class StrategyResponse(BaseModel):
    """An available resolution strategy."""
    name: str
    description: str


class ConflictStatsResponse(BaseModel):
    """Conflict resolution statistics."""
    total_conflicts: int
    resolved: int
    pending: int
    by_strategy: dict[str, int]
    by_type: dict[str, int]
