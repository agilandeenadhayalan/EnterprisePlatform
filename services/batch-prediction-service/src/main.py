"""
Batch Prediction Service — FastAPI application.

Batch scoring over datasets. Manages batch prediction jobs with status tracking,
result pagination, and job cancellation.

ROUTES:
  POST /batch/jobs              — Submit batch prediction job
  GET  /batch/jobs              — List batch jobs (?status=)
  GET  /batch/jobs/{id}         — Job details + progress
  GET  /batch/jobs/{id}/results — Get results (paginated)
  POST /batch/jobs/{id}/cancel  — Cancel job
  GET  /health                  — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query

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
    description="Batch scoring over datasets with job management",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/batch/jobs", response_model=schemas.BatchJobResponse, status_code=201)
async def create_batch_job(request: schemas.BatchJobCreateRequest):
    """Submit a new batch prediction job."""
    job = repository.repo.create_job(
        model_name=request.model_name,
        dataset_id=request.dataset_id,
        output_format=request.output_format,
    )
    return schemas.BatchJobResponse(**job.to_dict())


@app.get("/batch/jobs", response_model=schemas.BatchJobListResponse)
async def list_batch_jobs(
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List batch jobs, optionally filtered by status."""
    jobs = repository.repo.list_jobs(status=status)
    return schemas.BatchJobListResponse(
        jobs=[schemas.BatchJobResponse(**j.to_dict()) for j in jobs],
        total=len(jobs),
    )


@app.get("/batch/jobs/{job_id}", response_model=schemas.BatchJobResponse)
async def get_batch_job(job_id: str):
    """Get batch job details and progress."""
    job = repository.repo.get_job(job_id)
    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Batch job '{job_id}' not found")
    return schemas.BatchJobResponse(**job.to_dict())


@app.get("/batch/jobs/{job_id}/results", response_model=schemas.BatchResultListResponse)
async def get_batch_results(
    job_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Results per page"),
):
    """Get paginated results for a batch job."""
    job = repository.repo.get_job(job_id)
    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Batch job '{job_id}' not found")
    results, total = repository.repo.get_results(job_id, page=page, page_size=page_size)
    return schemas.BatchResultListResponse(
        results=[schemas.BatchResultResponse(**r.to_dict()) for r in results],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.post("/batch/jobs/{job_id}/cancel", response_model=schemas.BatchJobResponse)
async def cancel_batch_job(job_id: str):
    """Cancel a pending or running batch job."""
    job = repository.repo.cancel_job(job_id)
    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Batch job '{job_id}' not found")
    return schemas.BatchJobResponse(**job.to_dict())
