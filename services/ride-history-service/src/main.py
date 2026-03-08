"""
Ride History Service — FastAPI application.

ROUTES:
  GET /riders/{id}/history  — Get rider's trip history
  GET /riders/{id}/stats    — Get rider statistics
  GET /history/recent       — Get recent completed trips
  GET /health               — Health check
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine

import config as svc_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(svc_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Ride History Service",
    version="0.1.0",
    description="Read-only ride history and rider statistics",
    lifespan=lifespan,
)


@app.get("/riders/{rider_id}/history", response_model=schemas.HistoryListResponse)
async def get_rider_history(
    rider_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = repository.RideHistoryRepository(db)
    trips = await repo.get_rider_history(rider_id, limit=limit, offset=offset)
    return schemas.HistoryListResponse(
        trips=[_trip_response(t) for t in trips],
        count=len(trips),
    )


@app.get("/riders/{rider_id}/stats", response_model=schemas.RiderStatsResponse)
async def get_rider_stats(
    rider_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.RideHistoryRepository(db)
    stats = await repo.get_rider_stats(rider_id)
    return schemas.RiderStatsResponse(rider_id=rider_id, **stats)


@app.get("/history/recent", response_model=schemas.HistoryListResponse)
async def get_recent_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    repo = repository.RideHistoryRepository(db)
    trips = await repo.get_recent_completed(limit=limit)
    return schemas.HistoryListResponse(
        trips=[_trip_response(t) for t in trips],
        count=len(trips),
    )


def _trip_response(trip) -> schemas.HistoryTripResponse:
    return schemas.HistoryTripResponse(
        id=str(trip.id),
        rider_id=str(trip.rider_id),
        driver_id=str(trip.driver_id) if trip.driver_id else None,
        status=trip.status,
        pickup_address=trip.pickup_address,
        dropoff_address=trip.dropoff_address,
        actual_distance_km=trip.actual_distance_km,
        actual_duration_minutes=trip.actual_duration_minutes,
        fare_amount=trip.fare_amount,
        currency=trip.currency,
        vehicle_type=trip.vehicle_type,
        requested_at=trip.requested_at,
        completed_at=trip.completed_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
