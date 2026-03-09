"""
Batch Ingestion Service

Generic batch file ingestion service that accepts file metadata, validates
against known schemas, and stores data in MinIO Bronze layer. Produces
data.lake.ingested.v1 events upon successful ingestion.

Routes:
    POST /ingest            — Ingest a batch of records to Bronze layer
    GET  /ingest/history    — Ingestion history
    GET  /ingest/{job_id}   — Get ingestion job status
    GET  /ingest/schemas    — List known data schemas
    GET  /health            — Health check (provided by create_app)
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


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(service_config.settings.service_name, lifespan=lifespan)
repo = repository.ingestion_repo


def _job_to_response(job) -> schemas.IngestionJobResponse:
    return schemas.IngestionJobResponse(
        job_id=job.job_id,
        schema_name=job.schema_name,
        source=job.source,
        target_layer=job.target_layer,
        state=job.state.value,
        stats=schemas.IngestionStatsResponse(
            files_processed=job.stats.files_processed,
            total_bytes=job.stats.total_bytes,
            total_rows=job.stats.total_rows,
            failed_files=job.stats.failed_files,
        ),
        minio_path=job.minio_path,
        event_produced=job.event_produced,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@app.post("/ingest", response_model=schemas.IngestionJobResponse, status_code=201, tags=["Ingestion"])
async def ingest_batch(request: schemas.IngestRequest):
    """Ingest a batch of records to the Bronze layer in MinIO."""
    # Validate schema
    if not repo.schema_exists(request.schema_name):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown schema: '{request.schema_name}'. Use GET /ingest/schemas to see available schemas.",
        )

    # Validate file formats against schema
    for file in request.files:
        valid, error = repo.validate_schema(request.schema_name, file.format)
        if not valid:
            raise HTTPException(status_code=400, detail=error)

    # Create ingestion job
    job = repo.create_ingestion_job(
        schema_name=request.schema_name,
        source=request.source,
        target_layer=request.target_layer,
    )

    # Simulate ingestion
    total_bytes = sum(f.size_bytes for f in request.files)
    total_rows = sum(f.row_count or 0 for f in request.files)
    minio_path = f"s3://{request.target_layer}/{request.schema_name}/{job.job_id}/"

    repo.complete_job(
        job_id=job.job_id,
        files_processed=len(request.files),
        total_bytes=total_bytes,
        total_rows=total_rows,
        minio_path=minio_path,
    )

    completed = repo.get_job(job.job_id)
    return _job_to_response(completed)


@app.get("/ingest/history", response_model=schemas.IngestionHistoryResponse, tags=["Ingestion"])
async def ingestion_history():
    """Get ingestion history for all jobs."""
    jobs = repo.get_all_jobs()
    return schemas.IngestionHistoryResponse(
        jobs=[_job_to_response(j) for j in jobs],
        total=len(jobs),
    )


@app.get("/ingest/schemas", response_model=schemas.SchemasListResponse, tags=["Ingestion"])
async def list_schemas():
    """List all known data schemas for validation."""
    all_schemas = repo.get_all_schemas()
    schema_responses = [
        schemas.SchemaDefinition(
            name=s["name"],
            description=s["description"],
            required_columns=s["required_columns"],
            formats=s["formats"],
        )
        for s in all_schemas
    ]
    return schemas.SchemasListResponse(schemas=schema_responses, total=len(schema_responses))


@app.get("/ingest/{job_id}", response_model=schemas.IngestionJobResponse, tags=["Ingestion"])
async def get_ingestion_job(job_id: str):
    """Get the status of a specific ingestion job."""
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Ingestion job '{job_id}' not found")
    return _job_to_response(job)
