"""
Domain models for the conflict resolver service.

Manages conflict detection, CRDT merge operations, and resolution strategies.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ConflictType(str, Enum):
    """Types of conflicts that can occur."""
    WRITE_WRITE = "write_write"
    READ_WRITE = "read_write"
    SCHEMA = "schema"


class ResolutionStrategy(str, Enum):
    """Available resolution strategies."""
    LWW = "lww"
    MERGE = "merge"
    MANUAL = "manual"
    CRDT = "crdt"


class ConflictStatus(str, Enum):
    """Status of a conflict."""
    DETECTED = "detected"
    RESOLVING = "resolving"
    RESOLVED = "resolved"


class Conflict:
    """A conflict record."""

    def __init__(
        self,
        id: str,
        conflict_type: str,
        entity_id: str,
        version_a: dict[str, Any],
        version_b: dict[str, Any],
        resolution_strategy: Optional[str] = None,
        resolved_value: Optional[Any] = None,
        status: str = "detected",
        detected_at: Optional[datetime] = None,
        resolved_at: Optional[datetime] = None,
    ):
        self.id = id
        self.conflict_type = conflict_type
        self.entity_id = entity_id
        self.version_a = version_a
        self.version_b = version_b
        self.resolution_strategy = resolution_strategy
        self.resolved_value = resolved_value
        self.status = status
        self.detected_at = detected_at or datetime.utcnow()
        self.resolved_at = resolved_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conflict_type": self.conflict_type,
            "entity_id": self.entity_id,
            "version_a": self.version_a,
            "version_b": self.version_b,
            "resolution_strategy": self.resolution_strategy,
            "resolved_value": self.resolved_value,
            "status": self.status,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class MergeResult:
    """Result of a CRDT merge operation."""

    def __init__(
        self,
        merged_state: Any,
        merge_type: str,
        elements_merged: int,
    ):
        self.merged_state = merged_state
        self.merge_type = merge_type
        self.elements_merged = elements_merged

    def to_dict(self) -> dict:
        return {
            "merged_state": self.merged_state,
            "merge_type": self.merge_type,
            "elements_merged": self.elements_merged,
        }
