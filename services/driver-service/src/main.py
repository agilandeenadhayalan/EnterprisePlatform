"""
Driver Service — FastAPI application.

ROUTES:
  POST /drivers          — Register a new driver
  GET  /drivers          — List all drivers
  GET  /drivers/{id}     — Get driver by ID
  PATCH /drivers/{id}    — Update driver info
  GET  /drivers/nearby   — Find nearby available drivers
  GET  /health           — Health check (provided by create_app)
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
from mobility_common.fastapi.errors import conflict, not_found
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
    title="Driver Service",
    version="0.1.0",
    description="Driver registration and profile management for Smart Mobility Platform",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/drivers", response_model=schemas.DriverResponse, status_code=201)
async def register_driver(
    body: schemas.DriverCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new driver."""
    repo = repository.DriverRepository(db)

    existing = await repo.get_driver_by_email(body.email)
    if existing:
        raise conflict(f"Driver with email '{body.email}' already exists")

    driver = await repo.create_driver(**body.model_dump())

    # Publish event
    event = Event(
        event_type="driver.registered",
        source=service_config.settings.service_name,
        correlation_id=str(driver.id),
        payload={"driver_id": str(driver.id), "email": driver.email},
    )
    await app.state.producer.send_event(Topics.DRIVER_EVENTS, event)

    return _driver_response(driver)


@app.get("/drivers", response_model=schemas.DriverListResponse)
async def list_drivers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all drivers with pagination."""
    repo = repository.DriverRepository(db)
    drivers = await repo.list_drivers(skip=skip, limit=limit)
    total = await repo.count_drivers()
    return schemas.DriverListResponse(
        drivers=[_driver_response(d) for d in drivers],
        total=total,
    )


@app.get("/drivers/nearby", response_model=list[schemas.DriverResponse])
async def get_nearby_drivers(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_km: float = Query(5.0, gt=0, le=50),
    limit: int = Query(10, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Find nearby available drivers."""
    repo = repository.DriverRepository(db)
    drivers = await repo.find_nearby_drivers(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
    )
    return [_driver_response(d) for d in drivers]


@app.get("/drivers/{driver_id}", response_model=schemas.DriverResponse)
async def get_driver(
    driver_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a driver by ID."""
    repo = repository.DriverRepository(db)
    driver = await repo.get_driver_by_id(driver_id)
    if not driver:
        raise not_found("Driver", driver_id)
    return _driver_response(driver)


@app.patch("/drivers/{driver_id}", response_model=schemas.DriverResponse)
async def update_driver(
    driver_id: str,
    body: schemas.DriverUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update driver information."""
    repo = repository.DriverRepository(db)
    existing = await repo.get_driver_by_id(driver_id)
    if not existing:
        raise not_found("Driver", driver_id)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return _driver_response(existing)

    driver = await repo.update_driver(driver_id, **update_data)
    return _driver_response(driver)


def _driver_response(driver) -> schemas.DriverResponse:
    """Convert ORM model to response schema."""
    return schemas.DriverResponse(
        id=str(driver.id),
        user_id=str(driver.user_id),
        first_name=driver.first_name,
        last_name=driver.last_name,
        email=driver.email,
        phone=driver.phone,
        license_number=driver.license_number,
        vehicle_type=driver.vehicle_type,
        vehicle_make=driver.vehicle_make,
        vehicle_model=driver.vehicle_model,
        vehicle_year=driver.vehicle_year,
        vehicle_plate=driver.vehicle_plate,
        rating=driver.rating,
        total_trips=driver.total_trips,
        acceptance_rate=driver.acceptance_rate,
        is_active=driver.is_active,
        is_verified=driver.is_verified,
        status=driver.status,
        latitude=driver.latitude,
        longitude=driver.longitude,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
