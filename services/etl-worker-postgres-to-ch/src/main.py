"""
ETL Worker Postgres-to-ClickHouse Service

Syncs data from PostgreSQL to ClickHouse using incremental watermarks.
Supports both incremental (delta) and full resync modes.

Routes:
    POST /sync/{table_name}  — Sync a specific table (incremental or full)
    GET  /sync/status        — Status of all sync jobs
    GET  /sync/tables        — List syncable tables with last watermark
    POST /sync/full          — Trigger full resync of a table
    GET  /health             — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import HTTPException, Query

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository
from models import SyncMode, SyncState


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(service_config.settings.service_name, lifespan=lifespan)
repo = repository.sync_repo


@app.post("/sync/{table_name}", response_model=schemas.SyncJobResponse, tags=["Sync"])
async def sync_table(
    table_name: str,
    request: schemas.SyncRequest = schemas.SyncRequest(),
):
    """Sync a specific table from PostgreSQL to ClickHouse."""
    if not repo.table_exists(table_name):
        repo.add_table(table_name)

    mode = SyncMode.FULL if request.mode == "full" else SyncMode.INCREMENTAL
    job = repo.create_sync_job(table_name=table_name, mode=mode, batch_size=request.batch_size)

    # Simulate sync completion (in production, this would be async)
    import random
    rows = random.randint(100, 50000)
    repo.complete_job(job.job_id, rows_synced=rows)

    completed_job = repo.get_job(job.job_id)
    return schemas.SyncJobResponse(
        job_id=completed_job.job_id,
        table_name=completed_job.table_name,
        mode=completed_job.mode.value,
        state=completed_job.state.value,
        rows_synced=completed_job.rows_synced,
        error_message=completed_job.error_message,
        started_at=completed_job.started_at,
        completed_at=completed_job.completed_at,
    )


@app.get("/sync/status", response_model=schemas.SyncStatusResponse, tags=["Sync"])
async def sync_status():
    """Get status of all sync jobs."""
    all_jobs = repo.get_all_jobs()
    running = repo.get_jobs_by_state(SyncState.RUNNING)
    completed = repo.get_jobs_by_state(SyncState.COMPLETED)
    failed = repo.get_jobs_by_state(SyncState.FAILED)

    job_responses = [
        schemas.SyncJobResponse(
            job_id=j.job_id,
            table_name=j.table_name,
            mode=j.mode.value,
            state=j.state.value,
            rows_synced=j.rows_synced,
            error_message=j.error_message,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in all_jobs
    ]

    return schemas.SyncStatusResponse(
        total_jobs=len(all_jobs),
        running_jobs=len(running),
        completed_jobs=len(completed),
        failed_jobs=len(failed),
        jobs=job_responses,
    )


@app.get("/sync/tables", response_model=schemas.SyncTablesResponse, tags=["Sync"])
async def list_syncable_tables():
    """List all syncable tables with their last watermark."""
    watermarks = repo.get_all_watermarks()
    table_responses = [
        schemas.TableWatermarkResponse(
            table_name=wm.table_name,
            last_watermark=wm.last_watermark,
            rows_synced=wm.rows_synced,
            last_sync_at=wm.last_sync_at,
        )
        for wm in watermarks
    ]
    return schemas.SyncTablesResponse(tables=table_responses, total=len(table_responses))


@app.post("/sync/full", response_model=schemas.SyncJobResponse, tags=["Sync"])
async def full_resync(request: schemas.FullSyncRequest):
    """Trigger a full resync of a specific table, resetting its watermark."""
    if not repo.table_exists(request.table_name):
        raise HTTPException(status_code=404, detail=f"Table '{request.table_name}' not found")

    # Reset the watermark for full resync
    repo.reset_watermark(request.table_name)

    job = repo.create_sync_job(
        table_name=request.table_name,
        mode=SyncMode.FULL,
        batch_size=request.batch_size,
    )

    # Simulate full sync
    import random
    rows = random.randint(10000, 500000)
    repo.complete_job(job.job_id, rows_synced=rows)

    completed_job = repo.get_job(job.job_id)
    return schemas.SyncJobResponse(
        job_id=completed_job.job_id,
        table_name=completed_job.table_name,
        mode=completed_job.mode.value,
        state=completed_job.state.value,
        rows_synced=completed_job.rows_synced,
        error_message=completed_job.error_message,
        started_at=completed_job.started_at,
        completed_at=completed_job.completed_at,
    )
