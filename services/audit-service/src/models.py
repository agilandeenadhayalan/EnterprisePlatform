"""
Domain models for the audit service.

Immutable audit trail with hash chain for tamper detection.
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AuditAction(str, Enum):
    """Types of auditable actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    EXPORT = "export"
    APPROVE = "approve"


class AuditLog:
    """An immutable audit log entry with hash chain."""

    def __init__(
        self,
        id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        actor: str,
        details: Optional[dict[str, Any]] = None,
        region: Optional[str] = None,
        ip_address: Optional[str] = None,
        previous_hash: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.actor = actor
        self.details = details or {}
        self.region = region
        self.ip_address = ip_address
        self.created_at = created_at or datetime.utcnow()
        self.previous_hash = previous_hash or ""
        self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute hash of this entry for tamper detection."""
        payload = json.dumps({
            "id": self.id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actor": self.actor,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "created_at": self.created_at.isoformat(),
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actor": self.actor,
            "details": self.details,
            "region": self.region,
            "ip_address": self.ip_address,
            "entry_hash": self.entry_hash,
            "previous_hash": self.previous_hash,
            "created_at": self.created_at.isoformat(),
        }
