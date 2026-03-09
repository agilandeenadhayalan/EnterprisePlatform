"""
Domain models for the schema migration service.

Manages ClickHouse DDL versioning — like Alembic for ClickHouse.
Each migration has an up (apply) and down (rollback) SQL statement.
"""

from datetime import datetime
from typing import Optional


class Migration:
    """A schema migration with up/down SQL."""

    def __init__(
        self,
        id: str,
        version: int,
        name: str,
        description: str,
        sql_up: str,
        sql_down: str,
        status: str = "pending",
        applied_at: Optional[datetime] = None,
        rolled_back_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.version = version
        self.name = name
        self.description = description
        self.sql_up = sql_up
        self.sql_down = sql_down
        self.status = status  # pending, applied, rolled_back
        self.applied_at = applied_at
        self.rolled_back_at = rolled_back_at
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "sql_up": self.sql_up,
            "sql_down": self.sql_down,
            "status": self.status,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "rolled_back_at": self.rolled_back_at.isoformat() if self.rolled_back_at else None,
            "created_at": self.created_at.isoformat(),
        }


class MigrationStatus:
    """Current migration status summary."""

    def __init__(
        self,
        current_version: Optional[int],
        latest_version: Optional[int],
        total_migrations: int,
        pending_count: int,
        applied_count: int,
    ):
        self.current_version = current_version
        self.latest_version = latest_version
        self.total_migrations = total_migrations
        self.pending_count = pending_count
        self.applied_count = applied_count

    def to_dict(self) -> dict:
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "total_migrations": self.total_migrations,
            "pending_count": self.pending_count,
            "applied_count": self.applied_count,
        }
