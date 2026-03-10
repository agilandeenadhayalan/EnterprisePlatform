"""
Conflict Resolver repository — in-memory conflict and CRDT merge storage.

Manages conflict detection, resolution, and CRDT merge operations.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import Conflict, MergeResult


STRATEGIES = [
    {"name": "lww", "description": "Last-Writer-Wins — resolve by most recent timestamp"},
    {"name": "merge", "description": "Merge — combine both versions (for compatible types)"},
    {"name": "manual", "description": "Manual — require human decision"},
    {"name": "crdt", "description": "CRDT — conflict-free replicated data type merge"},
]


class ConflictRepository:
    """In-memory conflict storage and CRDT operations."""

    def __init__(self):
        self._conflicts: dict[str, Conflict] = {}

    # ── Conflict detection ──

    def detect_conflict(
        self,
        entity_id: str,
        version_a: dict[str, Any],
        version_b: dict[str, Any],
    ) -> Conflict:
        """Detect conflicts between two versions."""
        # Determine conflict type by comparing fields
        a_keys = set(version_a.keys()) - {"timestamp"}
        b_keys = set(version_b.keys()) - {"timestamp"}

        if a_keys != b_keys:
            conflict_type = "schema"
        else:
            conflict_type = "write_write"

        conflict_id = str(uuid.uuid4())
        conflict = Conflict(
            id=conflict_id,
            conflict_type=conflict_type,
            entity_id=entity_id,
            version_a=version_a,
            version_b=version_b,
            status="detected",
        )
        self._conflicts[conflict_id] = conflict
        return conflict

    # ── Conflict resolution ──

    def resolve_conflict(
        self,
        conflict_id: str,
        strategy: str,
        manual_value: Optional[Any] = None,
    ) -> Optional[Conflict]:
        """Resolve a conflict using the specified strategy."""
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return None

        conflict.resolution_strategy = strategy
        conflict.status = "resolved"
        conflict.resolved_at = datetime.utcnow()

        if strategy == "lww":
            # Last-Writer-Wins: compare timestamps
            ts_a = conflict.version_a.get("timestamp", "")
            ts_b = conflict.version_b.get("timestamp", "")
            conflict.resolved_value = conflict.version_a if ts_a >= ts_b else conflict.version_b
        elif strategy == "manual":
            conflict.resolved_value = manual_value
        elif strategy == "merge":
            # Merge common fields
            merged = {**conflict.version_a, **conflict.version_b}
            conflict.resolved_value = merged
        elif strategy == "crdt":
            merged = {**conflict.version_a, **conflict.version_b}
            conflict.resolved_value = merged

        return conflict

    # ── CRDT merge operations ──

    def crdt_merge(self, merge_type: str, state_a: Any, state_b: Any) -> MergeResult:
        """Perform a CRDT merge operation."""
        if merge_type == "counter":
            return self._merge_counter(state_a, state_b)
        elif merge_type == "set":
            return self._merge_set(state_a, state_b)
        elif merge_type == "register":
            return self._merge_register(state_a, state_b)
        else:
            raise ValueError(f"Unknown merge type: {merge_type}")

    def _merge_counter(self, state_a: dict, state_b: dict) -> MergeResult:
        """G-Counter merge: take max per key."""
        all_keys = set(list(state_a.keys()) + list(state_b.keys()))
        merged = {}
        for key in all_keys:
            merged[key] = max(state_a.get(key, 0), state_b.get(key, 0))
        return MergeResult(merged_state=merged, merge_type="counter", elements_merged=len(all_keys))

    def _merge_set(self, state_a: list, state_b: list) -> MergeResult:
        """G-Set merge: union of both sets."""
        merged = list(set(state_a) | set(state_b))
        return MergeResult(merged_state=sorted(merged), merge_type="set", elements_merged=len(merged))

    def _merge_register(self, state_a: dict, state_b: dict) -> MergeResult:
        """LWW-Register merge: latest timestamp wins."""
        ts_a = state_a.get("timestamp", "")
        ts_b = state_b.get("timestamp", "")
        winner = state_a if ts_a >= ts_b else state_b
        return MergeResult(merged_state=winner, merge_type="register", elements_merged=1)

    # ── Queries ──

    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """Get a conflict by ID."""
        return self._conflicts.get(conflict_id)

    def list_conflicts(self) -> list[Conflict]:
        """List all conflicts."""
        return list(self._conflicts.values())

    def get_strategies(self) -> list[dict]:
        """List available resolution strategies."""
        return STRATEGIES

    def get_stats(self) -> dict:
        """Get resolution statistics."""
        conflicts = list(self._conflicts.values())
        resolved = [c for c in conflicts if c.status == "resolved"]
        pending = [c for c in conflicts if c.status != "resolved"]

        by_strategy: dict[str, int] = {}
        for c in resolved:
            s = c.resolution_strategy or "unknown"
            by_strategy[s] = by_strategy.get(s, 0) + 1

        by_type: dict[str, int] = {}
        for c in conflicts:
            by_type[c.conflict_type] = by_type.get(c.conflict_type, 0) + 1

        return {
            "total_conflicts": len(conflicts),
            "resolved": len(resolved),
            "pending": len(pending),
            "by_strategy": by_strategy,
            "by_type": by_type,
        }


# Singleton repository instance
repo = ConflictRepository()
