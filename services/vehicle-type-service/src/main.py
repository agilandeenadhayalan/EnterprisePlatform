"""
Vehicle Type Service — FastAPI application.

ROUTES:
  GET /vehicle-types             — List all vehicle types
  GET /vehicle-types/{id}        — Get vehicle type details
  GET /vehicle-types/{id}/pricing — Get pricing for a vehicle type
  GET /health                    — Health check
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
    title="Vehicle Type Service",
    version="0.1.0",
    description="Vehicle type catalog and pricing tiers",
    lifespan=lifespan,
)


@app.get("/vehicle-types", response_model=schemas.VehicleTypeListResponse)
async def list_vehicle_types(db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleTypeRepository(db)
    types = await repo.list_vehicle_types()
    return schemas.VehicleTypeListResponse(
        vehicle_types=[_type_response(t) for t in types],
        count=len(types),
    )


@app.get("/vehicle-types/{type_id}", response_model=schemas.VehicleTypeResponse)
async def get_vehicle_type(type_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleTypeRepository(db)
    vtype = await repo.get_vehicle_type_by_id(type_id)
    if not vtype:
        raise not_found("VehicleType", type_id)
    return _type_response(vtype)


@app.get("/vehicle-types/{type_id}/pricing", response_model=schemas.VehicleTypePricingResponse)
async def get_vehicle_type_pricing(type_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.VehicleTypeRepository(db)
    vtype = await repo.get_vehicle_type_by_id(type_id)
    if not vtype:
        raise not_found("VehicleType", type_id)
    return schemas.VehicleTypePricingResponse(
        id=str(vtype.id),
        name=vtype.name,
        display_name=vtype.display_name,
        base_fare=vtype.base_fare,
        per_km_rate=vtype.per_km_rate,
        per_minute_rate=vtype.per_minute_rate,
        minimum_fare=vtype.minimum_fare,
        currency=vtype.currency,
    )


def _type_response(t) -> schemas.VehicleTypeResponse:
    return schemas.VehicleTypeResponse(
        id=str(t.id),
        name=t.name,
        display_name=t.display_name,
        description=t.description,
        capacity=t.capacity,
        luggage_capacity=t.luggage_capacity,
        is_active=t.is_active,
        features=t.features,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
