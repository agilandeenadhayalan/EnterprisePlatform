"""
Trip Service — FastAPI application.

ROUTES:
  POST   /trips              — Create a new trip
  GET    /trips/{id}         — Get trip details
  PATCH  /trips/{id}/status  — Update trip status
  GET    /trips              — List trips with filters
  GET    /riders/{id}/trips  — Get rider's trips
  GET    /health             — Health check (provided by create_app)

Produces events to ride.events.v1 topic.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, conflict
from mobility_common.events import Event, EventTypes
from mobility_common.kafka import EventProducer, Topics

import config as trip_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine and Kafka producer. Shutdown: close connections."""
    create_engine_and_session(trip_config.settings.database_url)
    producer = EventProducer(
        bootstrap_servers=trip_config.settings.kafka_bootstrap_servers,
        client_id="trip-service",
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()
    await dispose_engine()


app = create_app(
    title="Trip Service",
    version="0.1.0",
    description="Core trip management for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/trips", response_model=schemas.TripResponse, status_code=201)
async def create_trip(
    body: schemas.CreateTripRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new trip with status 'requested'."""
    repo = repository.TripRepository(db)

    trip = await repo.create_trip(
        rider_id=body.rider_id,
        pickup_latitude=body.pickup_latitude,
        pickup_longitude=body.pickup_longitude,
        pickup_address=body.pickup_address,
        dropoff_latitude=body.dropoff_latitude,
        dropoff_longitude=body.dropoff_longitude,
        dropoff_address=body.dropoff_address,
        vehicle_type=body.vehicle_type,
    )

    return _trip_response(trip)


@app.get("/trips/{trip_id}", response_model=schemas.TripResponse)
async def get_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get trip details by ID."""
    repo = repository.TripRepository(db)
    trip = await repo.get_trip_by_id(trip_id)
    if not trip:
        raise not_found("Trip", trip_id)
    return _trip_response(trip)


@app.patch("/trips/{trip_id}/status", response_model=schemas.TripResponse)
async def update_trip_status(
    trip_id: str,
    body: schemas.UpdateTripStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a trip's status following the valid state machine transitions."""
    repo = repository.TripRepository(db)
    trip = await repo.get_trip_by_id(trip_id)
    if not trip:
        raise not_found("Trip", trip_id)

    # Validate status transition
    allowed = repository.VALID_TRANSITIONS.get(trip.status, [])
    if body.status not in allowed:
        raise conflict(
            f"Cannot transition from '{trip.status}' to '{body.status}'. "
            f"Allowed: {allowed}"
        )

    updated = await repo.update_trip_status(
        trip_id=trip_id,
        new_status=body.status,
        driver_id=body.driver_id,
        vehicle_id=body.vehicle_id,
    )
    return _trip_response(updated)


@app.get("/trips", response_model=schemas.TripListResponse)
async def list_trips(
    status: Optional[str] = Query(None),
    rider_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List trips with optional status and rider_id filters."""
    repo = repository.TripRepository(db)
    trips = await repo.list_trips(
        status=status,
        rider_id=rider_id,
        limit=limit,
        offset=offset,
    )
    return schemas.TripListResponse(
        trips=[_trip_response(t) for t in trips],
        count=len(trips),
    )


@app.get("/riders/{rider_id}/trips", response_model=schemas.TripListResponse)
async def get_rider_trips(
    rider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all trips for a specific rider."""
    repo = repository.TripRepository(db)
    trips = await repo.get_rider_trips(rider_id)
    return schemas.TripListResponse(
        trips=[_trip_response(t) for t in trips],
        count=len(trips),
    )


def _trip_response(trip) -> schemas.TripResponse:
    """Convert a TripModel to a TripResponse."""
    return schemas.TripResponse(
        id=str(trip.id),
        rider_id=str(trip.rider_id),
        driver_id=str(trip.driver_id) if trip.driver_id else None,
        vehicle_id=str(trip.vehicle_id) if trip.vehicle_id else None,
        status=trip.status,
        pickup_latitude=trip.pickup_latitude,
        pickup_longitude=trip.pickup_longitude,
        pickup_address=trip.pickup_address,
        dropoff_latitude=trip.dropoff_latitude,
        dropoff_longitude=trip.dropoff_longitude,
        dropoff_address=trip.dropoff_address,
        estimated_distance_km=trip.estimated_distance_km,
        actual_distance_km=trip.actual_distance_km,
        estimated_duration_minutes=trip.estimated_duration_minutes,
        actual_duration_minutes=trip.actual_duration_minutes,
        fare_amount=trip.fare_amount,
        currency=trip.currency,
        vehicle_type=trip.vehicle_type,
        requested_at=trip.requested_at,
        started_at=trip.started_at,
        completed_at=trip.completed_at,
        cancelled_at=trip.cancelled_at,
        created_at=trip.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=trip_config.settings.service_port,
        reload=trip_config.settings.debug,
    )
