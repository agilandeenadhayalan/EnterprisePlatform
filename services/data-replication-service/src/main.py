"""
Data Replication Service — FastAPI application.

Replicates data between ClickHouse and MinIO. Supports ClickHouse to MinIO
(export as Parquet) and MinIO to ClickHouse (import) directions.

ROUTES:
  POST /replicate              — Start a replication job
  GET  /replicate/jobs         — List all replication jobs
  GET  /replicate/jobs/{id}    — Get job status
  POST /replicate/jobs/{id}/cancel — Cancel a running job
  GET  /health                 — Health check (provided by create_app)
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
    description="Data replication between ClickHouse and MinIO",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/replicate", response_model=schemas.ReplicationJobResponse, status_code=201)
async def start_replication(body: schemas.ReplicationRequest):
    """Start a new replication job."""
    valid_directions = ["ch_to_minio", "minio_to_ch"]
    if body.direction not in valid_directions:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid direction '{body.direction}'. Must be one of: {', '.join(valid_directions)}",
        )

    job = repository.repo.create_job(
        direction=body.direction,
        source=body.source,
        destination=body.destination,
        format=body.format,
    )
    return schemas.ReplicationJobResponse(**job.to_dict())


@app.get("/replicate/jobs", response_model=schemas.ReplicationJobListResponse)
async def list_jobs():
    """List all replication jobs."""
    jobs = repository.repo.list_jobs()
    return schemas.ReplicationJobListResponse(
        jobs=[schemas.ReplicationJobResponse(**j.to_dict()) for j in jobs],
        total=len(jobs),
    )


@app.get("/replicate/jobs/{job_id}", response_model=schemas.ReplicationJobResponse)
async def get_job(job_id: str):
    """Get the status of a replication job."""
    job = repository.repo.get_job(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return schemas.ReplicationJobResponse(**job.to_dict())


@app.post("/replicate/jobs/{job_id}/cancel", response_model=schemas.ReplicationJobResponse)
async def cancel_job(job_id: str):
    """Cancel a running replication job."""
    job = repository.repo.cancel_job(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return schemas.ReplicationJobResponse(**job.to_dict())
