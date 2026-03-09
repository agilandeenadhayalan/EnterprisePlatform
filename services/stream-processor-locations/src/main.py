"""
Stream Processor Locations — FastAPI application.

Processes driver location events and writes to ClickHouse fact_driver_locations.

ROUTES:
  POST /process          — Process location events batch
  GET  /process/stats    — Processing / buffer stats
  POST /process/flush    — Force flush buffered locations
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
_repo = repository.LocationProcessorRepository(
    buffer_max_size=service_config.settings.buffer_size,
    flush_interval_seconds=service_config.settings.flush_interval_seconds,
)


def get_repo() -> repository.LocationProcessorRepository:
    """Dependency — returns the location processor repository."""
    return _repo


@asynccontextmanager
async def lifespan(app):
    """Startup: initialize clients. Shutdown: flush and cleanup."""
    app.state.repo = _repo
    yield
    # Flush remaining buffer on shutdown
    _repo.flush()


app = create_app(
    title="Stream Processor Locations",
    version="0.1.0",
    description="Stream processor for driver location events — writes to ClickHouse fact_driver_locations",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/process", response_model=schemas.ProcessBatchResponse)
async def process_batch(
    body: schemas.ProcessBatchRequest,
    repo: repository.LocationProcessorRepository = Depends(get_repo),
):
    """Process a batch of location events — buffer and auto-flush."""
    results, flushed, failed = repo.process_batch(body.events)
    return schemas.ProcessBatchResponse(
        buffered=len(results),
        flushed=flushed,
        failed=failed,
        results=[
            schemas.ProcessedLocationResponse(
                driver_id=r.driver_id,
                latitude=r.latitude,
                longitude=r.longitude,
                zone_id=r.zone_id,
                zone_name=r.zone_name,
                speed_kmh=r.speed_kmh,
                status=r.status,
                processed_at=r.processed_at.isoformat(),
            )
            for r in results
        ],
    )


@app.get("/process/stats", response_model=schemas.BufferStatsResponse)
async def get_stats(
    repo: repository.LocationProcessorRepository = Depends(get_repo),
):
    """Return current buffer and processing statistics."""
    stats = repo.get_stats()
    return schemas.BufferStatsResponse(
        buffer_size=stats.buffer_size,
        total_received=stats.total_received,
        total_flushed=stats.total_flushed,
        total_errors=stats.total_errors,
        flush_count=stats.flush_count,
        last_flush_at=stats.last_flush_at,
        last_received_at=stats.last_received_at,
        uptime_seconds=stats.uptime_seconds,
    )


@app.post("/process/flush", response_model=schemas.FlushResponse)
async def force_flush(
    repo: repository.LocationProcessorRepository = Depends(get_repo),
):
    """Force flush all buffered location records."""
    flushed = repo.flush()
    return schemas.FlushResponse(
        flushed=flushed,
        status="flushed",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
