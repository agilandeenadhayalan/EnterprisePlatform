"""
Surge Service — FastAPI application.

ROUTES:
  GET  /surge/{zone_id}    — Get surge multiplier for a zone
  PUT  /surge/{zone_id}    — Update surge multiplier
  GET  /surge/active       — List zones with active surge
  POST /surge/calculate    — Calculate surge from supply/demand
  GET  /health             — Health check (provided by create_app)
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
from mobility_common.kafka import EventProducer, Topics
from mobility_common.events import Event, EventTypes

import config as surge_config
import models  # noqa: F401
import schemas
import repository
import calculator


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine and Kafka producer. Shutdown: close connections."""
    create_engine_and_session(surge_config.settings.database_url)
    producer = EventProducer(
        bootstrap_servers=surge_config.settings.kafka_bootstrap_servers,
        client_id="surge-service",
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()
    await dispose_engine()


app = create_app(
    title="Surge Service",
    version="0.1.0",
    description="Dynamic surge pricing for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/surge/active", response_model=schemas.SurgeActiveListResponse)
async def list_active_surge(db: AsyncSession = Depends(get_db)):
    """List all zones with active surge pricing."""
    repo = repository.SurgeRepository(db)
    zones = await repo.list_active_zones()
    return schemas.SurgeActiveListResponse(
        zones=[
            schemas.SurgeZoneResponse(
                id=str(z.id), zone_id=z.zone_id, zone_name=z.zone_name,
                surge_multiplier=z.surge_multiplier, demand_count=z.demand_count,
                supply_count=z.supply_count, is_active=z.is_active,
                last_calculated_at=z.last_calculated_at, created_at=z.created_at,
            )
            for z in zones
        ],
        count=len(zones),
    )


@app.get("/surge/{zone_id}", response_model=schemas.SurgeZoneResponse)
async def get_surge(zone_id: str, db: AsyncSession = Depends(get_db)):
    """Get the current surge multiplier for a zone."""
    repo = repository.SurgeRepository(db)
    zone = await repo.get_zone(zone_id)
    if not zone:
        raise not_found("SurgeZone", zone_id)
    return schemas.SurgeZoneResponse(
        id=str(zone.id), zone_id=zone.zone_id, zone_name=zone.zone_name,
        surge_multiplier=zone.surge_multiplier, demand_count=zone.demand_count,
        supply_count=zone.supply_count, is_active=zone.is_active,
        last_calculated_at=zone.last_calculated_at, created_at=zone.created_at,
    )


@app.put("/surge/{zone_id}", response_model=schemas.SurgeZoneResponse)
async def update_surge(
    zone_id: str, body: schemas.SurgeUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update the surge multiplier for a zone."""
    repo = repository.SurgeRepository(db)
    zone = await repo.get_zone(zone_id)
    if not zone:
        raise not_found("SurgeZone", zone_id)

    updated = await repo.update_zone(
        zone_id=zone_id, surge_multiplier=body.surge_multiplier,
        demand_count=body.demand_count, supply_count=body.supply_count,
    )

    # Produce Kafka event
    event = Event(
        event_type=EventTypes.SURGE_UPDATED,
        source="surge-service",
        correlation_id=zone_id,
        payload={
            "zone_id": zone_id,
            "surge_multiplier": body.surge_multiplier,
        },
    )
    await app.state.producer.send_event(Topics.SURGE_UPDATES, event)

    return schemas.SurgeZoneResponse(
        id=str(updated.id), zone_id=updated.zone_id, zone_name=updated.zone_name,
        surge_multiplier=updated.surge_multiplier, demand_count=updated.demand_count,
        supply_count=updated.supply_count, is_active=updated.is_active,
        last_calculated_at=updated.last_calculated_at, created_at=updated.created_at,
    )


@app.post("/surge/calculate", response_model=schemas.SurgeCalculateResponse)
async def calculate_surge(body: schemas.SurgeCalculateRequest):
    """Calculate surge multiplier from supply/demand counts (stateless)."""
    multiplier = calculator.calculate_surge(body.demand_count, body.supply_count)
    return schemas.SurgeCalculateResponse(
        zone_id=body.zone_id,
        demand_count=body.demand_count,
        supply_count=body.supply_count,
        calculated_multiplier=multiplier,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=surge_config.settings.service_port, reload=surge_config.settings.debug)
