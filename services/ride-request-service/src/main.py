"""
Ride Request Service — FastAPI application.

ROUTES:
  POST   /requests            — Create a new ride request
  GET    /requests/{id}       — Get ride request details
  GET    /requests/{id}/status — Get request status
  DELETE /requests/{id}       — Cancel a ride request
  GET    /health              — Health check
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
from mobility_common.kafka import EventProducer

import config as svc_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(svc_config.settings.database_url)
    producer = EventProducer(
        bootstrap_servers=svc_config.settings.kafka_bootstrap_servers,
        client_id="ride-request-service",
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()
    await dispose_engine()


app = create_app(
    title="Ride Request Service",
    version="0.1.0",
    description="Ride request lifecycle management",
    lifespan=lifespan,
)


@app.post("/requests", response_model=schemas.RideRequestResponse, status_code=201)
async def create_request(
    body: schemas.CreateRideRequestRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.RideRequestRepository(db)
    req = await repo.create_request(
        rider_id=body.rider_id,
        pickup_latitude=body.pickup_latitude,
        pickup_longitude=body.pickup_longitude,
        pickup_address=body.pickup_address,
        dropoff_latitude=body.dropoff_latitude,
        dropoff_longitude=body.dropoff_longitude,
        dropoff_address=body.dropoff_address,
        vehicle_type=body.vehicle_type,
    )
    return _response(req)


@app.get("/requests/{request_id}", response_model=schemas.RideRequestResponse)
async def get_request(request_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RideRequestRepository(db)
    req = await repo.get_request_by_id(request_id)
    if not req:
        raise not_found("RideRequest", request_id)
    return _response(req)


@app.get("/requests/{request_id}/status", response_model=schemas.RideRequestStatusResponse)
async def get_request_status(request_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RideRequestRepository(db)
    req = await repo.get_request_by_id(request_id)
    if not req:
        raise not_found("RideRequest", request_id)
    return schemas.RideRequestStatusResponse(
        id=str(req.id),
        status=req.status,
        updated_at=req.updated_at,
    )


@app.delete("/requests/{request_id}", status_code=204)
async def cancel_request(request_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RideRequestRepository(db)
    req = await repo.get_request_by_id(request_id)
    if not req:
        raise not_found("RideRequest", request_id)
    await repo.cancel_request(request_id)


def _response(req) -> schemas.RideRequestResponse:
    return schemas.RideRequestResponse(
        id=str(req.id),
        rider_id=str(req.rider_id),
        status=req.status,
        pickup_latitude=req.pickup_latitude,
        pickup_longitude=req.pickup_longitude,
        pickup_address=req.pickup_address,
        dropoff_latitude=req.dropoff_latitude,
        dropoff_longitude=req.dropoff_longitude,
        dropoff_address=req.dropoff_address,
        vehicle_type=req.vehicle_type,
        estimated_fare=req.estimated_fare,
        created_at=req.created_at,
        expires_at=req.expires_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
