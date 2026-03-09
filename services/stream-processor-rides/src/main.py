"""
Stream Processor Rides — FastAPI application.

Simulates consuming ride events from Kafka and writing to ClickHouse fact_rides.

ROUTES:
  POST /process          — Process a batch of ride events
  GET  /process/stats    — Processing statistics
  POST /process/replay   — Replay events from a time range
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
_repo = repository.RideProcessorRepository()


def get_repo() -> repository.RideProcessorRepository:
    """Dependency — returns the ride processor repository."""
    return _repo


@asynccontextmanager
async def lifespan(app):
    """Startup: initialize ClickHouse client. Shutdown: cleanup."""
    # In production, connect to ClickHouse and Kafka here
    app.state.repo = _repo
    yield


app = create_app(
    title="Stream Processor Rides",
    version="0.1.0",
    description="Stream processor for ride events — transforms and writes to ClickHouse fact_rides",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/process", response_model=schemas.ProcessBatchResponse)
async def process_batch(
    body: schemas.ProcessBatchRequest,
    repo: repository.RideProcessorRepository = Depends(get_repo),
):
    """Process a batch of ride events — transform and store as fact records."""
    results, failed = repo.process_batch(body.events)
    return schemas.ProcessBatchResponse(
        processed=len(results),
        failed=failed,
        results=[
            schemas.ProcessedRideResponse(
                ride_id=r.ride_id,
                driver_id=r.driver_id,
                rider_id=r.rider_id,
                fare_amount=r.fare_amount,
                total_amount=r.total_amount,
                trip_duration_minutes=r.trip_duration_minutes,
                speed_mph=r.speed_mph,
                pickup_hour=r.pickup_hour,
                pickup_day_of_week=r.pickup_day_of_week,
                is_weekend=r.is_weekend,
                processed_at=r.processed_at.isoformat(),
            )
            for r in results
        ],
    )


@app.get("/process/stats", response_model=schemas.ProcessingStatsResponse)
async def get_stats(
    repo: repository.RideProcessorRepository = Depends(get_repo),
):
    """Return current processing statistics."""
    stats = repo.get_stats()
    return schemas.ProcessingStatsResponse(
        events_processed=stats.events_processed,
        events_failed=stats.events_failed,
        error_count=stats.error_count,
        last_processed_at=stats.last_processed_at,
        avg_processing_time_ms=stats.avg_processing_time_ms,
        uptime_seconds=stats.uptime_seconds,
    )


@app.post("/process/replay", response_model=schemas.ReplayResponse)
async def replay_events(
    body: schemas.ReplayRequest,
    repo: repository.RideProcessorRepository = Depends(get_repo),
):
    """Replay events from a time range (returns matching processed rides)."""
    rides = repo.get_rides_in_range(body.start_time, body.end_time)
    return schemas.ReplayResponse(
        status="completed",
        replayed_count=len(rides),
        start_time=body.start_time,
        end_time=body.end_time,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
