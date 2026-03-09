"""
Domain models for the data retention service.

Manages TTL (time-to-live) policies for ClickHouse tables and MinIO buckets.
"""

from datetime import datetime
from typing import Any, Optional


class RetentionPolicy:
    """A data retention policy defining TTL for a target."""

    def __init__(
        self,
        id: str,
        name: str,
        target: str,
        target_type: str,
        retention_days: int,
        description: Optional[str] = None,
        enabled: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.target = target  # table name or bucket/prefix
        self.target_type = target_type  # "clickhouse" or "minio"
        self.retention_days = retention_days
        self.description = description or ""
        self.enabled = enabled
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "target": self.target,
            "target_type": self.target_type,
            "retention_days": self.retention_days,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RetentionRun:
    """Result of a retention enforcement run."""

    def __init__(
        self,
        id: str,
        policy_id: str,
        policy_name: str,
        target: str,
        records_deleted: int = 0,
        bytes_reclaimed: int = 0,
        status: str = "completed",
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ):
        self.id = id
        self.policy_id = policy_id
        self.policy_name = policy_name
        self.target = target
        self.records_deleted = records_deleted
        self.bytes_reclaimed = bytes_reclaimed
        self.status = status
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at or datetime.utcnow()
        self.error = error

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "target": self.target,
            "records_deleted": self.records_deleted,
            "bytes_reclaimed": self.bytes_reclaimed,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }
