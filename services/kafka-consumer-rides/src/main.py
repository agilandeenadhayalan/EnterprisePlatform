"""
Kafka Consumer Rides — FastAPI application.

Archives ride events to MinIO Bronze layer as compressed JSON files.

ROUTES:
  POST /archive          — Archive a batch of events to MinIO Bronze
  GET  /archive/stats    — Archive statistics
  GET  /archive/files    — List archived files
  GET  /health           — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Query

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository

# Module-level repository instance
_repo = repository.RideArchiveRepository(
    bucket=service_config.settings.archive_bucket,
    prefix=service_config.settings.archive_prefix,
)


def get_repo() -> repository.RideArchiveRepository:
    """Dependency — returns the ride archive repository."""
    return _repo


@asynccontextmanager
async def lifespan(app):
    """Startup: initialize MinIO client. Shutdown: cleanup."""
    app.state.repo = _repo
    yield


app = create_app(
    title="Kafka Consumer Rides",
    version="0.1.0",
    description="Archives ride events to MinIO Bronze layer as compressed JSON",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/archive", response_model=schemas.ArchiveBatchResponse)
async def archive_batch(
    body: schemas.ArchiveBatchRequest,
    repo: repository.RideArchiveRepository = Depends(get_repo),
):
    """Archive a batch of ride events to MinIO Bronze layer."""
    file_path, file_size = repo.archive_batch(body.events, body.topic)
    return schemas.ArchiveBatchResponse(
        archived=len(body.events),
        file_path=file_path,
        file_size=file_size,
        status="archived",
    )


@app.get("/archive/stats", response_model=schemas.ArchiveStatsResponse)
async def get_stats(
    repo: repository.RideArchiveRepository = Depends(get_repo),
):
    """Return archive statistics."""
    stats = repo.get_stats()
    return schemas.ArchiveStatsResponse(
        events_archived=stats.events_archived,
        files_written=stats.files_written,
        bytes_written=stats.bytes_written,
        errors=stats.errors,
        last_archived_at=stats.last_archived_at,
        uptime_seconds=stats.uptime_seconds,
    )


@app.get("/archive/files", response_model=schemas.ArchivedFilesListResponse)
async def list_files(
    repo: repository.RideArchiveRepository = Depends(get_repo),
):
    """List all archived files."""
    files = repo.list_files()
    return schemas.ArchivedFilesListResponse(
        files=[
            schemas.ArchivedFileResponse(
                file_path=f.file_path,
                file_size=f.file_size,
                event_count=f.event_count,
                created_at=f.created_at,
                topic=f.topic,
            )
            for f in files
        ],
        total=len(files),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
