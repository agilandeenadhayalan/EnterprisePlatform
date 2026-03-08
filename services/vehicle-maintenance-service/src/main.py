"""
Vehicle Maintenance Service — FastAPI application.

ROUTES:
  POST /maintenance                  — Create a maintenance record
  GET  /vehicles/{id}/maintenance    — Get maintenance history for a vehicle
  GET  /maintenance/upcoming         — Get upcoming scheduled maintenance
  GET  /health                       — Health check
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
    title="Vehicle Maintenance Service",
    version="0.1.0",
    description="Vehicle maintenance tracking and scheduling",
    lifespan=lifespan,
)


@app.post("/maintenance", response_model=schemas.MaintenanceResponse, status_code=201)
async def create_maintenance(
    body: schemas.CreateMaintenanceRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.VehicleMaintenanceRepository(db)
    record = await repo.create_maintenance(
        vehicle_id=body.vehicle_id,
        maintenance_type=body.maintenance_type,
        description=body.description,
        cost=body.cost,
        service_provider=body.service_provider,
        scheduled_at=body.scheduled_at,
        next_due_at=body.next_due_at,
    )
    return _maintenance_response(record)


@app.get("/vehicles/{vehicle_id}/maintenance", response_model=schemas.MaintenanceListResponse)
async def get_vehicle_maintenance(vehicle_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleMaintenanceRepository(db)
    records = await repo.get_vehicle_maintenance(vehicle_id)
    return schemas.MaintenanceListResponse(
        records=[_maintenance_response(r) for r in records],
        count=len(records),
    )


@app.get("/maintenance/upcoming", response_model=schemas.MaintenanceListResponse)
async def get_upcoming_maintenance(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    repo = repository.VehicleMaintenanceRepository(db)
    records = await repo.get_upcoming_maintenance(limit=limit)
    return schemas.MaintenanceListResponse(
        records=[_maintenance_response(r) for r in records],
        count=len(records),
    )


def _maintenance_response(r) -> schemas.MaintenanceResponse:
    return schemas.MaintenanceResponse(
        id=str(r.id),
        vehicle_id=str(r.vehicle_id),
        maintenance_type=r.maintenance_type,
        status=r.status,
        description=r.description,
        cost=r.cost,
        currency=r.currency,
        service_provider=r.service_provider,
        parts_replaced=r.parts_replaced,
        scheduled_at=r.scheduled_at,
        started_at=r.started_at,
        completed_at=r.completed_at,
        next_due_at=r.next_due_at,
        created_at=r.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
