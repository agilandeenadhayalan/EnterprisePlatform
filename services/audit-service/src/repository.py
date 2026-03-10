"""
Audit repository — append-only in-memory audit log with hash chain.

Manages immutable audit entries with tamper detection via hash chaining.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import AuditLog


class AuditRepository:
    """Append-only in-memory audit log with hash chain."""

    def __init__(self):
        self._logs: list[AuditLog] = []
        self._logs_by_id: dict[str, AuditLog] = {}
        self._last_hash: str = ""

    # ── Append-only logging ──

    def create_log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        actor: str,
        details: Optional[dict[str, Any]] = None,
        region: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Append a new audit log entry (immutable, no update or delete)."""
        log_id = str(uuid.uuid4())
        log = AuditLog(
            id=log_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            details=details,
            region=region,
            ip_address=ip_address,
            previous_hash=self._last_hash,
        )
        self._logs.append(log)
        self._logs_by_id[log_id] = log
        self._last_hash = log.entry_hash
        return log

    def get_log(self, log_id: str) -> Optional[AuditLog]:
        """Get a specific log entry."""
        return self._logs_by_id.get(log_id)

    # ── Queries ──

    def list_logs(
        self,
        entity_type: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
    ) -> list[AuditLog]:
        """List logs with optional filters."""
        results = self._logs
        if entity_type:
            results = [l for l in results if l.entity_type == entity_type]
        if actor:
            results = [l for l in results if l.actor == actor]
        if action:
            results = [l for l in results if l.action == action]
        return results

    def logs_for_entity(self, entity_type: str, entity_id: str) -> list[AuditLog]:
        """Get logs for a specific entity."""
        return [
            l for l in self._logs
            if l.entity_type == entity_type and l.entity_id == entity_id
        ]

    def logs_by_actor(self, actor: str) -> list[AuditLog]:
        """Get logs by actor."""
        return [l for l in self._logs if l.actor == actor]

    def search_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        region: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[AuditLog]:
        """Advanced search with multiple filters."""
        results = self._logs
        if entity_type:
            results = [l for l in results if l.entity_type == entity_type]
        if entity_id:
            results = [l for l in results if l.entity_id == entity_id]
        if actor:
            results = [l for l in results if l.actor == actor]
        if action:
            results = [l for l in results if l.action == action]
        if region:
            results = [l for l in results if l.region == region]
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            results = [l for l in results if l.created_at >= start_dt]
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            results = [l for l in results if l.created_at <= end_dt]
        return results

    # ── Stats ──

    def get_stats(self) -> dict:
        """Get audit statistics."""
        by_action: dict[str, int] = {}
        by_entity_type: dict[str, int] = {}
        by_actor: dict[str, int] = {}

        for log in self._logs:
            by_action[log.action] = by_action.get(log.action, 0) + 1
            by_entity_type[log.entity_type] = by_entity_type.get(log.entity_type, 0) + 1
            by_actor[log.actor] = by_actor.get(log.actor, 0) + 1

        return {
            "total_entries": len(self._logs),
            "by_action": by_action,
            "by_entity_type": by_entity_type,
            "by_actor": by_actor,
            "chain_valid": self._validate_chain(),
        }

    def _validate_chain(self) -> bool:
        """Validate the hash chain integrity."""
        prev_hash = ""
        for log in self._logs:
            if log.previous_hash != prev_hash:
                return False
            prev_hash = log.entry_hash
        return True


# Singleton repository instance
repo = AuditRepository()
