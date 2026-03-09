"""
Pydantic request/response schemas for the schema migration API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class MigrationCreate(BaseModel):
    """POST /migrations — create a new migration."""
    version: int = Field(..., gt=0, description="Migration version number")
    name: str = Field(..., description="Short migration name (e.g., 'add_ride_events_table')")
    description: str = Field(..., description="What this migration does")
    sql_up: str = Field(..., description="SQL to apply the migration")
    sql_down: str = Field(..., description="SQL to rollback the migration")


# ── Response schemas ──

class MigrationResponse(BaseModel):
    """A migration record."""
    id: str
    version: int
    name: str
    description: str
    sql_up: str
    sql_down: str
    status: str
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    created_at: datetime


class MigrationListResponse(BaseModel):
    """List of migrations."""
    migrations: list[MigrationResponse]
    total: int


class MigrationStatusResponse(BaseModel):
    """Current migration status."""
    current_version: Optional[int] = None
    latest_version: Optional[int] = None
    total_migrations: int
    pending_count: int
    applied_count: int


class MigrationRunResponse(BaseModel):
    """Response from applying or rolling back migrations."""
    action: str  # "apply" or "rollback"
    migrations_affected: list[MigrationResponse]
    count: int
