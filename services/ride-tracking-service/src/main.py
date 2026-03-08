"""
Ride Tracking Service — FastAPI application.

ROUTES:
  POST /trips/{id}/waypoints      — Add a waypoint to a trip's track
  GET  /trips/{id}/track          — Get full track for a trip
  GET  /trips/{id}/track/latest   — Get latest waypoint
  GET  /health                    — Health check
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found

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
    title="Ride Tracking Service",
    version="0.1.0",
    description="GPS waypoint tracking during trips",
    lifespan=lifespan,
)


@app.post("/trips/{trip_id}/waypoints", response_model=schemas.WaypointResponse, status_code=201)
async def add_waypoint(
    trip_id: str,
    body: schemas.AddWaypointRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.RideTrackingRepository(db)
    wp = await repo.add_waypoint(
        trip_id=trip_id,
        latitude=body.latitude,
        longitude=body.longitude,
        altitude=body.altitude,
        speed_kmh=body.speed_kmh,
        heading=body.heading,
        accuracy_meters=body.accuracy_meters,
    )
    return _wp_response(wp)


@app.get("/trips/{trip_id}/track", response_model=schemas.TrackResponse)
async def get_track(trip_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RideTrackingRepository(db)
    waypoints = await repo.get_track(trip_id)
    return schemas.TrackResponse(
        trip_id=trip_id,
        waypoints=[_wp_response(wp) for wp in waypoints],
        count=len(waypoints),
    )


@app.get("/trips/{trip_id}/track/latest", response_model=schemas.WaypointResponse)
async def get_latest_waypoint(trip_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RideTrackingRepository(db)
    wp = await repo.get_latest_waypoint(trip_id)
    if not wp:
        raise not_found("Waypoint", trip_id)
    return _wp_response(wp)


def _wp_response(wp) -> schemas.WaypointResponse:
    return schemas.WaypointResponse(
        id=str(wp.id),
        trip_id=str(wp.trip_id),
        latitude=wp.latitude,
        longitude=wp.longitude,
        altitude=wp.altitude,
        speed_kmh=wp.speed_kmh,
        heading=wp.heading,
        accuracy_meters=wp.accuracy_meters,
        sequence_number=wp.sequence_number,
        recorded_at=wp.recorded_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
