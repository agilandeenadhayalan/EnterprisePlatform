"""
Schema Migration repository — in-memory migration history.

Manages ClickHouse DDL versioning with version ordering,
idempotent apply, and rollback support.
"""

import uuid
from datetime import datetime
from typing import Optional

from models import Migration, MigrationStatus


class MigrationRepository:
    """In-memory migration storage with version ordering."""

    def __init__(self):
        self._migrations: dict[str, Migration] = {}

    def create_migration(
        self,
        version: int,
        name: str,
        description: str,
        sql_up: str,
        sql_down: str,
    ) -> Migration:
        """Create a new migration."""
        # Check for duplicate version
        for m in self._migrations.values():
            if m.version == version:
                raise ValueError(f"Migration version {version} already exists")

        migration_id = str(uuid.uuid4())
        migration = Migration(
            id=migration_id,
            version=version,
            name=name,
            description=description,
            sql_up=sql_up,
            sql_down=sql_down,
        )
        self._migrations[migration_id] = migration
        return migration

    def get_migration(self, migration_id: str) -> Optional[Migration]:
        """Get a migration by ID."""
        return self._migrations.get(migration_id)

    def list_migrations(self) -> list[Migration]:
        """List all migrations ordered by version."""
        return sorted(self._migrations.values(), key=lambda m: m.version)

    def get_pending_migrations(self) -> list[Migration]:
        """Get all pending (unapplied) migrations in version order."""
        return [
            m for m in self.list_migrations()
            if m.status == "pending"
        ]

    def get_applied_migrations(self) -> list[Migration]:
        """Get all applied migrations in version order."""
        return [
            m for m in self.list_migrations()
            if m.status == "applied"
        ]

    def apply_pending(self) -> list[Migration]:
        """
        Apply all pending migrations in version order.

        Idempotent: already-applied migrations are skipped.
        Simulates executing sql_up against ClickHouse.
        """
        pending = self.get_pending_migrations()
        applied: list[Migration] = []

        for migration in pending:
            migration.status = "applied"
            migration.applied_at = datetime.utcnow()
            migration.rolled_back_at = None
            applied.append(migration)

        return applied

    def rollback_last(self) -> Optional[Migration]:
        """
        Rollback the last applied migration.

        Simulates executing sql_down against ClickHouse.
        """
        applied = self.get_applied_migrations()
        if not applied:
            return None

        # Rollback the highest-version applied migration
        last = applied[-1]
        last.status = "rolled_back"
        last.rolled_back_at = datetime.utcnow()
        return last

    def get_status(self) -> MigrationStatus:
        """Get current migration status."""
        all_migrations = self.list_migrations()
        applied = [m for m in all_migrations if m.status == "applied"]
        pending = [m for m in all_migrations if m.status == "pending"]

        current_version = applied[-1].version if applied else None
        latest_version = all_migrations[-1].version if all_migrations else None

        return MigrationStatus(
            current_version=current_version,
            latest_version=latest_version,
            total_migrations=len(all_migrations),
            pending_count=len(pending),
            applied_count=len(applied),
        )


# Singleton repository instance
repo = MigrationRepository()
