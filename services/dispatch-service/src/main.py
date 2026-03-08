"""
Dispatch Service — FastAPI application.

ROUTES:
  POST /dispatch               — Assign a driver to a trip
  GET  /dispatch/{id}/status    — Get assignment status
  GET  /trips/{id}/assignments  — Get all assignments for a trip
  GET  /zones                   — List dispatch zones
  GET  /health                  — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found
from mobility_common.kafka import EventProducer, Topics
from mobility_common.events import Event, EventTypes

import config as dispatch_config
import models  # noqa: F401
import schemas
import repository
import scoring


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine and Kafka producer. Shutdown: close connections."""
    create_engine_and_session(dispatch_config.settings.database_url)
    producer = EventProducer(
        bootstrap_servers=dispatch_config.settings.kafka_bootstrap_servers,
        client_id="dispatch-service",
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()
    await dispose_engine()


app = create_app(
    title="Dispatch Service",
    version="0.1.0",
    description="Driver dispatch and assignment for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/dispatch", response_model=schemas.DispatchAssignmentResponse, status_code=201)
async def create_dispatch(
    body: schemas.DispatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Assign a driver to a trip.

    Calculates a dispatch score based on distance, rating, acceptance rate,
    and cancellation rate, then creates the assignment record.
    """
    repo = repository.DispatchRepository(db)

    # Calculate driver score
    driver_score = scoring.score_driver(
        distance=body.distance_to_pickup or 0.0,
        rating=body.driver_rating or 4.0,
        acceptance_rate=body.acceptance_rate or 0.8,
        cancellation_rate=body.cancellation_rate or 0.05,
    )

    assignment = await repo.create_assignment(
        trip_id=body.trip_id,
        driver_id=body.driver_id,
        score=driver_score,
        distance_to_pickup=body.distance_to_pickup,
    )

    # Produce Kafka event
    event = Event(
        event_type=EventTypes.RIDE_DRIVER_ASSIGNED,
        source="dispatch-service",
        correlation_id=body.trip_id,
        payload={
            "assignment_id": str(assignment.id),
            "trip_id": body.trip_id,
            "driver_id": body.driver_id,
            "score": driver_score,
        },
    )
    await app.state.producer.send_event(Topics.DISPATCH_ASSIGNMENTS, event)

    return schemas.DispatchAssignmentResponse(
        id=str(assignment.id),
        trip_id=str(assignment.trip_id),
        driver_id=str(assignment.driver_id),
        status=assignment.status,
        score=assignment.score,
        distance_to_pickup=assignment.distance_to_pickup,
        assigned_at=assignment.assigned_at,
        responded_at=assignment.responded_at,
        created_at=assignment.created_at,
    )


@app.get("/dispatch/{assignment_id}/status", response_model=schemas.DispatchStatusResponse)
async def get_dispatch_status(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the status of a dispatch assignment."""
    repo = repository.DispatchRepository(db)
    assignment = await repo.get_assignment_by_id(assignment_id)
    if not assignment:
        raise not_found("Assignment", assignment_id)

    return schemas.DispatchStatusResponse(
        id=str(assignment.id),
        status=assignment.status,
        score=assignment.score,
        assigned_at=assignment.assigned_at,
        responded_at=assignment.responded_at,
    )


@app.get("/trips/{trip_id}/assignments", response_model=schemas.TripAssignmentsResponse)
async def get_trip_assignments(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all dispatch assignments for a trip."""
    repo = repository.DispatchRepository(db)
    assignments = await repo.get_trip_assignments(trip_id)

    return schemas.TripAssignmentsResponse(
        trip_id=trip_id,
        assignments=[
            schemas.DispatchAssignmentResponse(
                id=str(a.id),
                trip_id=str(a.trip_id),
                driver_id=str(a.driver_id),
                status=a.status,
                score=a.score,
                distance_to_pickup=a.distance_to_pickup,
                assigned_at=a.assigned_at,
                responded_at=a.responded_at,
                created_at=a.created_at,
            )
            for a in assignments
        ],
        count=len(assignments),
    )


@app.get("/zones", response_model=schemas.ZoneListResponse)
async def list_zones(
    db: AsyncSession = Depends(get_db),
):
    """List all dispatch zones."""
    repo = repository.DispatchRepository(db)
    zones = await repo.list_zones()

    return schemas.ZoneListResponse(
        zones=[
            schemas.DispatchZoneResponse(
                id=str(z.id),
                name=z.name,
                city=z.city,
                lat_min=z.lat_min,
                lat_max=z.lat_max,
                lon_min=z.lon_min,
                lon_max=z.lon_max,
                is_active=z.is_active,
                created_at=z.created_at,
            )
            for z in zones
        ],
        count=len(zones),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=dispatch_config.settings.service_port,
        reload=dispatch_config.settings.debug,
    )
