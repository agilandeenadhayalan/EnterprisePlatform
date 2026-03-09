"""
ML Training Service — FastAPI application.

PyTorch/sklearn training orchestrator. Manages training jobs including
submission, status tracking, cancellation, and model architecture listing.

ROUTES:
  POST /training/jobs                — Submit a training job
  GET  /training/jobs                — List training jobs (?status=)
  GET  /training/jobs/{job_id}       — Get job details + metrics
  POST /training/jobs/{job_id}/cancel — Cancel a running job
  GET  /training/models              — List available model architectures
  GET  /training/jobs/{job_id}/logs  — Training logs
  GET  /health                       — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query, HTTPException

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
    description="PyTorch/sklearn training orchestrator for ML model training jobs",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/training/jobs", response_model=schemas.TrainingJobResponse, status_code=201)
async def submit_training_job(body: schemas.TrainingJobCreateRequest):
    """Submit a new training job."""
    job = repository.repo.create_job(
        model_type=body.model_type,
        hyperparameters=body.hyperparameters,
        dataset_id=body.dataset_id,
    )
    return schemas.TrainingJobResponse(**job.to_dict())


@app.get("/training/jobs", response_model=schemas.TrainingJobListResponse)
async def list_training_jobs(
    status: Optional[str] = Query(default=None, description="Filter by status: pending, running, completed, failed, cancelled"),
):
    """List all training jobs, optionally filtered by status."""
    jobs = repository.repo.list_jobs(status=status)
    return schemas.TrainingJobListResponse(
        jobs=[schemas.TrainingJobResponse(**j.to_dict()) for j in jobs],
        total=len(jobs),
    )


@app.get("/training/jobs/{job_id}", response_model=schemas.TrainingJobResponse)
async def get_training_job(job_id: str):
    """Get details for a specific training job including metrics."""
    job = repository.repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
    return schemas.TrainingJobResponse(**job.to_dict())


@app.post("/training/jobs/{job_id}/cancel", response_model=schemas.TrainingJobResponse)
async def cancel_training_job(job_id: str):
    """Cancel a pending or running training job."""
    job = repository.repo.cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
    return schemas.TrainingJobResponse(**job.to_dict())


@app.get("/training/models", response_model=schemas.ModelArchitectureListResponse)
async def list_model_architectures():
    """List all available model architectures."""
    archs = repository.repo.list_architectures()
    return schemas.ModelArchitectureListResponse(
        architectures=[schemas.ModelArchitectureResponse(**a.to_dict()) for a in archs],
        total=len(archs),
    )


@app.get("/training/jobs/{job_id}/logs", response_model=schemas.TrainingLogResponse)
async def get_training_logs(job_id: str):
    """Get training logs for a specific job."""
    job = repository.repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
    return schemas.TrainingLogResponse(
        job_id=job.id,
        logs=job.logs,
        total=len(job.logs),
    )
