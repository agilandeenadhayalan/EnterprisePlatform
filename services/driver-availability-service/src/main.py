"""
Driver Availability Service — FastAPI application.

ROUTES:
  POST /drivers/{id}/online    — Set driver as online
  POST /drivers/{id}/offline   — Set driver as offline
  GET  /drivers/{id}/status    — Get driver availability status
  GET  /available              — List all available (online) drivers
  GET  /health                 — Health check (provided by create_app)
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
from mobility_common.events import Event, EventTypes

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
    title="Driver Availability Service",
    version="0.1.0",
    description="Driver online/offline status management",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/drivers/{driver_id}/online", response_model=schemas.AvailabilityResponse)
async def go_online(
    driver_id: str,
    body: schemas.GoOnlineRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set a driver as online (available for trips)."""
    repo = repository.AvailabilityRepository(db)
    record = await repo.set_online(driver_id, latitude=body.latitude, longitude=body.longitude)

    event = Event(
        event_type=EventTypes.DRIVER_WENT_ONLINE,
        source=service_config.settings.service_name,
        correlation_id=driver_id,
        payload={"driver_id": driver_id, "latitude": body.latitude, "longitude": body.longitude},
    )
    await app.state.producer.send_event(Topics.DRIVER_STATUS, event)

    return _availability_response(record)


@app.post("/drivers/{driver_id}/offline", response_model=schemas.AvailabilityResponse)
async def go_offline(
    driver_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Set a driver as offline (unavailable for trips)."""
    repo = repository.AvailabilityRepository(db)
    record = await repo.set_offline(driver_id)

    event = Event(
        event_type=EventTypes.DRIVER_WENT_OFFLINE,
        source=service_config.settings.service_name,
        correlation_id=driver_id,
        payload={"driver_id": driver_id},
    )
    await app.state.producer.send_event(Topics.DRIVER_STATUS, event)

    return _availability_response(record)


@app.get("/drivers/{driver_id}/status", response_model=schemas.AvailabilityResponse)
async def get_status(
    driver_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the current availability status for a driver."""
    repo = repository.AvailabilityRepository(db)
    record = await repo.get_by_driver_id(driver_id)
    if not record:
        raise not_found("Driver availability", driver_id)
    return _availability_response(record)


@app.get("/available", response_model=schemas.AvailableDriversResponse)
async def list_available(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all currently available (online) drivers."""
    repo = repository.AvailabilityRepository(db)
    drivers = await repo.get_available_drivers(skip=skip, limit=limit)
    total = await repo.count_available()
    return schemas.AvailableDriversResponse(
        drivers=[_availability_response(d) for d in drivers],
        total=total,
    )


def _availability_response(record) -> schemas.AvailabilityResponse:
    """Convert ORM model to response schema."""
    return schemas.AvailabilityResponse(
        id=str(record.id),
        driver_id=str(record.driver_id),
        status=record.status,
        latitude=record.latitude,
        longitude=record.longitude,
        last_online_at=record.last_online_at,
        last_offline_at=record.last_offline_at,
        total_online_seconds=record.total_online_seconds,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
