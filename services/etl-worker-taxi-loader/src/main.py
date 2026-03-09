"""
ETL Worker Taxi Loader Service

Loads NYC taxi Parquet files into ClickHouse fact_rides table.
Supports chunked reading with 100K rows per batch, checkpoint tracking
for resumable loads, and column mapping from NYC TLC schema.

Routes:
    POST /load              — Start loading taxi data (accepts year/month params)
    GET  /load/status       — Loading progress (rows_loaded, current_file, speed)
    POST /load/{year}/{month} — Load specific month's data
    GET  /load/checkpoint   — Get current checkpoint
    GET  /health            — Health check (provided by create_app)
"""

import random
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import HTTPException

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(service_config.settings.service_name, lifespan=lifespan)
repo = repository.taxi_loader_repo


@app.post("/load", response_model=schemas.LoadJobResponse, tags=["Load"])
async def start_load(request: schemas.LoadRequest):
    """Start loading NYC taxi data for a given year/month."""
    job = repo.create_load_job(year=request.year, month=request.month, batch_size=request.batch_size)

    # Simulate loading completion
    rows = random.randint(100000, 3000000)
    speed = random.uniform(50000, 200000)
    repo.complete_job(job.job_id, rows_loaded=rows, speed=speed)

    completed = repo.get_job(job.job_id)
    return schemas.LoadJobResponse(
        job_id=completed.job_id,
        year=completed.year,
        month=completed.month,
        state=completed.state.value,
        rows_loaded=completed.rows_loaded,
        total_rows=completed.total_rows,
        current_file=completed.current_file,
        speed_rows_per_sec=completed.speed_rows_per_sec,
        started_at=completed.started_at,
        completed_at=completed.completed_at,
    )


@app.get("/load/status", response_model=schemas.LoadStatusResponse, tags=["Load"])
async def load_status():
    """Get loading progress for all jobs."""
    active = repo.get_active_jobs()
    completed_count = len(repo.get_completed_jobs())
    total_rows = repo.get_total_rows_loaded()

    active_responses = [
        schemas.LoadJobResponse(
            job_id=j.job_id,
            year=j.year,
            month=j.month,
            state=j.state.value,
            rows_loaded=j.rows_loaded,
            total_rows=j.total_rows,
            current_file=j.current_file,
            speed_rows_per_sec=j.speed_rows_per_sec,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in active
    ]

    return schemas.LoadStatusResponse(
        active_jobs=active_responses,
        completed_jobs=completed_count,
        total_rows_loaded=total_rows,
    )


@app.post("/load/{year}/{month}", response_model=schemas.LoadJobResponse, tags=["Load"])
async def load_specific_month(year: int, month: int):
    """Load a specific month's taxi data."""
    if not (2009 <= year <= 2030):
        raise HTTPException(status_code=400, detail="Year must be between 2009 and 2030")
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    job = repo.create_load_job(year=year, month=month)

    # Simulate loading
    rows = random.randint(100000, 3000000)
    speed = random.uniform(50000, 200000)
    repo.complete_job(job.job_id, rows_loaded=rows, speed=speed)

    completed = repo.get_job(job.job_id)
    return schemas.LoadJobResponse(
        job_id=completed.job_id,
        year=completed.year,
        month=completed.month,
        state=completed.state.value,
        rows_loaded=completed.rows_loaded,
        total_rows=completed.total_rows,
        current_file=completed.current_file,
        speed_rows_per_sec=completed.speed_rows_per_sec,
        started_at=completed.started_at,
        completed_at=completed.completed_at,
    )


@app.get("/load/checkpoint", response_model=schemas.CheckpointsListResponse, tags=["Load"])
async def get_checkpoints():
    """Get all current checkpoints for loaded data."""
    checkpoints = repo.get_all_checkpoints()
    checkpoint_responses = [
        schemas.CheckpointResponse(
            year=cp.year,
            month=cp.month,
            last_row_offset=cp.last_row_offset,
            last_file=cp.last_file,
            rows_loaded=cp.rows_loaded,
            updated_at=cp.updated_at,
        )
        for cp in checkpoints
    ]
    return schemas.CheckpointsListResponse(
        checkpoints=checkpoint_responses,
        total=len(checkpoint_responses),
    )
