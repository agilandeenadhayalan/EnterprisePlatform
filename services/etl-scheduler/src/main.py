"""
ETL Scheduler Service

Manages scheduled ETL jobs with cron-like scheduling. Provides full CRUD
for job definitions, manual triggering, and execution history tracking.
Implements a job state machine: idle -> running -> completed/failed.

Routes:
    GET    /jobs                  — List all scheduled jobs
    POST   /jobs                  — Create a new scheduled job
    GET    /jobs/{job_id}         — Get job details
    PATCH  /jobs/{job_id}         — Update job schedule/config
    DELETE /jobs/{job_id}         — Delete a job
    POST   /jobs/{job_id}/trigger — Manually trigger a job
    GET    /jobs/{job_id}/history — Job execution history
    GET    /health                — Health check (provided by create_app)
"""

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
from models import JobConfig


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(service_config.settings.service_name, lifespan=lifespan)
repo = repository.scheduler_repo


def _job_to_response(job) -> schemas.JobResponse:
    return schemas.JobResponse(
        job_id=job.job_id,
        name=job.name,
        description=job.description,
        cron_schedule=schemas.CronScheduleResponse(**job.cron_schedule.to_dict()),
        config=schemas.JobConfigSchema(
            target_service=job.config.target_service,
            target_endpoint=job.config.target_endpoint,
            payload=job.config.payload,
            timeout_seconds=job.config.timeout_seconds,
            retry_count=job.config.retry_count,
            retry_delay_seconds=job.config.retry_delay_seconds,
        ),
        state=job.state.value,
        enabled=job.enabled,
        created_at=job.created_at,
        updated_at=job.updated_at,
        last_run_at=job.last_run_at,
        next_run_at=job.next_run_at,
    )


def _execution_to_response(execution) -> schemas.ExecutionResponse:
    return schemas.ExecutionResponse(
        execution_id=execution.execution_id,
        job_id=execution.job_id,
        state=execution.state.value,
        rows_processed=execution.rows_processed,
        error_message=execution.error_message,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        duration_seconds=execution.duration_seconds,
    )


@app.get("/jobs", response_model=schemas.JobListResponse, tags=["Jobs"])
async def list_jobs():
    """List all scheduled ETL jobs."""
    jobs = repo.get_all_jobs()
    return schemas.JobListResponse(
        jobs=[_job_to_response(j) for j in jobs],
        total=len(jobs),
    )


@app.post("/jobs", response_model=schemas.JobResponse, status_code=201, tags=["Jobs"])
async def create_job(request: schemas.CreateJobRequest):
    """Create a new scheduled ETL job."""
    try:
        config = JobConfig(
            target_service=request.config.target_service,
            target_endpoint=request.config.target_endpoint,
            payload=request.config.payload,
            timeout_seconds=request.config.timeout_seconds,
            retry_count=request.config.retry_count,
            retry_delay_seconds=request.config.retry_delay_seconds,
        )
        job = repo.create_job(
            name=request.name,
            description=request.description,
            cron_expression=request.cron_expression,
            config=config,
            enabled=request.enabled,
        )
        return _job_to_response(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/jobs/{job_id}", response_model=schemas.JobResponse, tags=["Jobs"])
async def get_job(job_id: str):
    """Get details of a specific scheduled job."""
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return _job_to_response(job)


@app.patch("/jobs/{job_id}", response_model=schemas.JobResponse, tags=["Jobs"])
async def update_job(job_id: str, request: schemas.UpdateJobRequest):
    """Update a scheduled job's configuration or schedule."""
    if not repo.job_exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    config = None
    if request.config:
        config = JobConfig(
            target_service=request.config.target_service,
            target_endpoint=request.config.target_endpoint,
            payload=request.config.payload,
            timeout_seconds=request.config.timeout_seconds,
            retry_count=request.config.retry_count,
            retry_delay_seconds=request.config.retry_delay_seconds,
        )

    try:
        job = repo.update_job(
            job_id=job_id,
            name=request.name,
            description=request.description,
            cron_expression=request.cron_expression,
            config=config,
            enabled=request.enabled,
        )
        return _job_to_response(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/jobs/{job_id}", status_code=204, tags=["Jobs"])
async def delete_job(job_id: str):
    """Delete a scheduled job."""
    if not repo.delete_job(job_id):
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")


@app.post("/jobs/{job_id}/trigger", response_model=schemas.TriggerResponse, tags=["Jobs"])
async def trigger_job(job_id: str):
    """Manually trigger a scheduled job execution."""
    if not repo.job_exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    execution = repo.trigger_job(job_id)
    return schemas.TriggerResponse(
        execution_id=execution.execution_id,
        job_id=job_id,
        message="Job triggered successfully",
        state=execution.state.value,
    )


@app.get("/jobs/{job_id}/history", response_model=schemas.ExecutionHistoryResponse, tags=["Jobs"])
async def job_history(job_id: str):
    """Get execution history for a scheduled job."""
    if not repo.job_exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    executions = repo.get_job_history(job_id)
    return schemas.ExecutionHistoryResponse(
        executions=[_execution_to_response(e) for e in executions],
        total=len(executions),
    )
