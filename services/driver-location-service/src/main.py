"""
Driver Location Service — FastAPI application.

ROUTES:
  POST /locations                        — Update driver location
  GET  /drivers/{id}/location            — Get latest location
  GET  /drivers/{id}/location/history    — Get location history
  GET  /health                           — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found
from mobility_common.kafka import EventProducer, Topics
from mobility_common.events import Event

import config as service_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine and Kafka producer. Shutdown: close connections."""
    create_engine_and_session(service_config.settings.database_url)
    producer = EventProducer(
        bootstrap_servers=service_config.settings.kafka_bootstrap_servers,
        client_id=service_config.settings.service_name,
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()
    await dispose_engine()


app = create_app(
    title="Driver Location Service",
    version="0.1.0",
    description="Real-time driver location tracking and history",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/locations", response_model=schemas.LocationResponse, status_code=201)
async def update_location(
    body: schemas.LocationUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a new location update for a driver."""
    repo = repository.LocationRepository(db)
    location = await repo.create_location(**body.model_dump())

    # Publish location event
    event = Event(
        event_type="driver.location.updated",
        source=service_config.settings.service_name,
        correlation_id=body.driver_id,
        payload={
            "driver_id": body.driver_id,
            "latitude": body.latitude,
            "longitude": body.longitude,
            "heading": body.heading,
            "speed": body.speed,
        },
    )
    await app.state.producer.send_event(Topics.DRIVER_LOCATION, event)

    return _location_response(location)


@app.get("/drivers/{driver_id}/location", response_model=schemas.LocationResponse)
async def get_latest_location(
    driver_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent location for a driver."""
    repo = repository.LocationRepository(db)
    location = await repo.get_latest_location(driver_id)
    if not location:
        raise not_found("Location", driver_id)
    return _location_response(location)


@app.get("/drivers/{driver_id}/location/history", response_model=schemas.LocationHistoryResponse)
async def get_location_history(
    driver_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get location history for a driver."""
    repo = repository.LocationRepository(db)
    locations = await repo.get_location_history(driver_id, skip=skip, limit=limit)
    total = await repo.count_locations(driver_id)
    return schemas.LocationHistoryResponse(
        locations=[_location_response(loc) for loc in locations],
        total=total,
    )


def _location_response(location) -> schemas.LocationResponse:
    """Convert ORM model to response schema."""
    return schemas.LocationResponse(
        id=str(location.id),
        driver_id=str(location.driver_id),
        latitude=location.latitude,
        longitude=location.longitude,
        heading=location.heading,
        speed=location.speed,
        accuracy=location.accuracy,
        source=location.source,
        recorded_at=location.recorded_at,
        created_at=location.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
