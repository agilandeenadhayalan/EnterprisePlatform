"""
Failover Manager Service — FastAPI application.

Health monitoring, failover triggers, and region promotion.

ROUTES:
  GET    /failover/status           — Failover status for all regions
  POST   /failover/events           — Record a failover event
  GET    /failover/events           — List failover history
  GET    /failover/events/{id}      — Get event details
  POST   /failover/trigger          — Trigger failover
  POST   /failover/promote/{code}   — Promote region to primary
  GET    /failover/health           — Region health summary
  GET    /health                    — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Health monitoring, failover triggers, and region promotion",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/failover/status", response_model=list[schemas.FailoverStatusResponse])
async def failover_status():
    """Failover status for all regions."""
    return repository.repo.get_failover_status()


@app.post("/failover/events", response_model=schemas.FailoverEventResponse, status_code=201)
async def create_event(body: schemas.FailoverEventCreate):
    """Record a failover event."""
    event = repository.repo.create_event(
        source_region=body.source_region,
        target_region=body.target_region,
        trigger_type=body.trigger_type,
        reason=body.reason,
        status=body.status,
    )
    return schemas.FailoverEventResponse(**event.to_dict())


@app.get("/failover/events", response_model=list[schemas.FailoverEventResponse])
async def list_events():
    """List failover history."""
    events = repository.repo.list_events()
    return [schemas.FailoverEventResponse(**e.to_dict()) for e in events]


@app.get("/failover/events/{event_id}", response_model=schemas.FailoverEventResponse)
async def get_event(event_id: str):
    """Get failover event details."""
    event = repository.repo.get_event(event_id)
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Failover event '{event_id}' not found")
    return schemas.FailoverEventResponse(**event.to_dict())


@app.post("/failover/trigger", response_model=schemas.FailoverEventResponse)
async def trigger_failover(body: schemas.FailoverTrigger):
    """Trigger a failover from source to target region."""
    event = repository.repo.trigger_failover(
        source_region=body.source_region,
        target_region=body.target_region,
        reason=body.reason,
    )
    return schemas.FailoverEventResponse(**event.to_dict())


@app.post("/failover/promote/{region_code}", response_model=schemas.RegionHealthResponse)
async def promote_region(region_code: str):
    """Promote a region to primary."""
    health = repository.repo.promote_region(region_code)
    return schemas.RegionHealthResponse(**health.to_dict())


@app.get("/failover/health", response_model=list[schemas.RegionHealthResponse])
async def health_summary():
    """Region health summary."""
    healths = repository.repo.list_health()
    return [schemas.RegionHealthResponse(**h.to_dict()) for h in healths]
