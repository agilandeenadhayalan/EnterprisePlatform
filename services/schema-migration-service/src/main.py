"""
Schema Migration Service — FastAPI application.

Manages ClickHouse DDL versioning — like Alembic for ClickHouse.
Supports creating migrations with up/down SQL, applying pending migrations
in version order, and rolling back the last applied migration.

ROUTES:
  GET  /migrations         — List all migrations
  POST /migrations         — Create a new migration
  POST /migrations/apply   — Apply all pending migrations
  POST /migrations/rollback — Rollback last applied migration
  GET  /migrations/status  — Current migration status (version, pending count)
  GET  /health             — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="ClickHouse DDL versioning and schema migration management",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/migrations", response_model=schemas.MigrationListResponse)
async def list_migrations():
    """List all migrations ordered by version."""
    migrations = repository.repo.list_migrations()
    return schemas.MigrationListResponse(
        migrations=[schemas.MigrationResponse(**m.to_dict()) for m in migrations],
        total=len(migrations),
    )


@app.post("/migrations", response_model=schemas.MigrationResponse, status_code=201)
async def create_migration(body: schemas.MigrationCreate):
    """Create a new migration with up/down SQL."""
    try:
        migration = repository.repo.create_migration(
            version=body.version,
            name=body.name,
            description=body.description,
            sql_up=body.sql_up,
            sql_down=body.sql_down,
        )
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=str(e))

    return schemas.MigrationResponse(**migration.to_dict())


@app.post("/migrations/apply", response_model=schemas.MigrationRunResponse)
async def apply_migrations():
    """Apply all pending migrations in version order (idempotent)."""
    applied = repository.repo.apply_pending()
    return schemas.MigrationRunResponse(
        action="apply",
        migrations_affected=[schemas.MigrationResponse(**m.to_dict()) for m in applied],
        count=len(applied),
    )


@app.post("/migrations/rollback", response_model=schemas.MigrationRunResponse)
async def rollback_migration():
    """Rollback the last applied migration using sql_down."""
    migration = repository.repo.rollback_last()
    if not migration:
        return schemas.MigrationRunResponse(
            action="rollback",
            migrations_affected=[],
            count=0,
        )
    return schemas.MigrationRunResponse(
        action="rollback",
        migrations_affected=[schemas.MigrationResponse(**migration.to_dict())],
        count=1,
    )


@app.get("/migrations/status", response_model=schemas.MigrationStatusResponse)
async def migration_status():
    """Get current migration status — latest version and pending count."""
    status = repository.repo.get_status()
    return schemas.MigrationStatusResponse(**status.to_dict())
