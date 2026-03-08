"""
Vehicle Service — FastAPI application.

ROUTES:
  POST   /vehicles              — Register a new vehicle
  GET    /vehicles              — List all vehicles
  GET    /vehicles/{id}         — Get vehicle details
  PUT    /vehicles/{id}         — Update vehicle
  DELETE /vehicles/{id}         — Delete vehicle
  GET    /vehicles/{id}/status  — Get vehicle status
  GET    /drivers/{id}/vehicle  — Get driver's assigned vehicle
  GET    /health                — Health check
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
from mobility_common.fastapi.errors import not_found, conflict

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
    title="Vehicle Service",
    version="0.1.0",
    description="Fleet vehicle management",
    lifespan=lifespan,
)


@app.post("/vehicles", response_model=schemas.VehicleResponse, status_code=201)
async def create_vehicle(
    body: schemas.CreateVehicleRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.VehicleRepository(db)
    vehicle = await repo.create_vehicle(
        make=body.make,
        model=body.model,
        year=body.year,
        color=body.color,
        license_plate=body.license_plate,
        driver_id=body.driver_id,
        vehicle_type_id=body.vehicle_type_id,
        vin=body.vin,
        capacity=body.capacity,
    )
    return _vehicle_response(vehicle)


@app.get("/vehicles", response_model=schemas.VehicleListResponse)
async def list_vehicles(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = repository.VehicleRepository(db)
    vehicles = await repo.list_vehicles(limit=limit, offset=offset)
    return schemas.VehicleListResponse(
        vehicles=[_vehicle_response(v) for v in vehicles],
        count=len(vehicles),
    )


@app.get("/vehicles/{vehicle_id}", response_model=schemas.VehicleResponse)
async def get_vehicle(vehicle_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleRepository(db)
    vehicle = await repo.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise not_found("Vehicle", vehicle_id)
    return _vehicle_response(vehicle)


@app.put("/vehicles/{vehicle_id}", response_model=schemas.VehicleResponse)
async def update_vehicle(
    vehicle_id: str,
    body: schemas.UpdateVehicleRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.VehicleRepository(db)
    vehicle = await repo.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise not_found("Vehicle", vehicle_id)

    updates = body.model_dump(exclude_none=True)
    if updates:
        vehicle = await repo.update_vehicle(vehicle_id, **updates)
    return _vehicle_response(vehicle)


@app.delete("/vehicles/{vehicle_id}", status_code=204)
async def delete_vehicle(vehicle_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleRepository(db)
    vehicle = await repo.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise not_found("Vehicle", vehicle_id)
    await repo.delete_vehicle(vehicle_id)


@app.get("/vehicles/{vehicle_id}/status", response_model=schemas.VehicleStatusResponse)
async def get_vehicle_status(vehicle_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleRepository(db)
    vehicle = await repo.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise not_found("Vehicle", vehicle_id)
    return schemas.VehicleStatusResponse(
        id=str(vehicle.id),
        status=vehicle.status,
        is_active=vehicle.is_active,
    )


@app.get("/drivers/{driver_id}/vehicle", response_model=schemas.VehicleResponse)
async def get_driver_vehicle(driver_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleRepository(db)
    vehicle = await repo.get_driver_vehicle(driver_id)
    if not vehicle:
        raise not_found("Vehicle for driver", driver_id)
    return _vehicle_response(vehicle)


def _vehicle_response(v) -> schemas.VehicleResponse:
    return schemas.VehicleResponse(
        id=str(v.id),
        driver_id=str(v.driver_id) if v.driver_id else None,
        vehicle_type_id=str(v.vehicle_type_id) if v.vehicle_type_id else None,
        make=v.make,
        model=v.model,
        year=v.year,
        color=v.color,
        license_plate=v.license_plate,
        vin=v.vin,
        status=v.status,
        capacity=v.capacity,
        is_active=v.is_active,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
