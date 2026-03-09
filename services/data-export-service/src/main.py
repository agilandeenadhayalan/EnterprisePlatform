"""
Data Export Service — FastAPI application.

Exports query results to downloadable formats (CSV, Parquet, JSON, XLSX).
Manages async export jobs with status tracking and download URLs.

ROUTES:
  POST   /export           — Start an export job (query, format, destination)
  GET    /export/jobs       — List all export jobs
  GET    /export/jobs/{id}  — Get export job status and download URL
  DELETE /export/jobs/{id}  — Cancel or delete an export job
  GET    /export/formats    — List supported export formats
  GET    /health            — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException

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
    description="Export query results to downloadable formats (CSV, Parquet, JSON, XLSX)",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/export", response_model=schemas.ExportJobResponse, status_code=201)
async def start_export(body: schemas.ExportRequest):
    """Start a new export job with the specified query and format."""
    # Validate format
    if body.format not in repository.VALID_FORMAT_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: '{body.format}'. "
                   f"Supported: {sorted(repository.VALID_FORMAT_IDS)}",
        )

    # Validate query is not empty
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")

    job = repository.repo.create_job(
        query=body.query,
        format=body.format,
        destination=body.destination,
    )
    return schemas.ExportJobResponse(**job.to_dict())


@app.get("/export/jobs", response_model=schemas.ExportJobListResponse)
async def list_export_jobs():
    """List all export jobs."""
    jobs = repository.repo.list_jobs()
    return schemas.ExportJobListResponse(
        jobs=[schemas.ExportJobResponse(**j.to_dict()) for j in jobs],
        total=len(jobs),
    )


@app.get("/export/jobs/{job_id}", response_model=schemas.ExportJobResponse)
async def get_export_job(job_id: str):
    """Get export job status, including download URL when complete."""
    job = repository.repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Export job '{job_id}' not found")
    return schemas.ExportJobResponse(**job.to_dict())


@app.delete("/export/jobs/{job_id}", status_code=204)
async def delete_export_job(job_id: str):
    """Cancel or delete an export job."""
    deleted = repository.repo.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Export job '{job_id}' not found")


@app.get("/export/formats", response_model=schemas.ExportFormatListResponse)
async def list_export_formats():
    """List supported export formats with descriptions."""
    formats = repository.repo.get_formats()
    return schemas.ExportFormatListResponse(
        formats=[schemas.ExportFormatResponse(**f.to_dict()) for f in formats],
        total=len(formats),
    )
