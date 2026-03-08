"""
Device Service — FastAPI application.

ROUTES:
  POST   /devices                    — Register a device
  GET    /devices                    — List current user's devices (requires auth)
  GET    /devices/{device_id}        — Get device details
  PUT    /devices/{device_id}/trust  — Mark device as trusted (requires auth)
  DELETE /devices/{device_id}        — Remove a device
  GET    /health                     — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, conflict, forbidden
from mobility_common.fastapi.middleware import get_current_user, TokenPayload

import config as device_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(device_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Device Service",
    version="0.1.0",
    description="Device registration and trust management for Smart Mobility Platform",
    lifespan=lifespan,
)


# -- Helper --

def _device_response(device) -> schemas.DeviceResponse:
    """Convert a DeviceModel to a DeviceResponse."""
    return schemas.DeviceResponse(
        id=str(device.id),
        user_id=str(device.user_id),
        device_id=device.device_id,
        device_name=device.device_name,
        device_type=device.device_type,
        os=device.os,
        browser=device.browser,
        fingerprint=device.fingerprint,
        is_trusted=device.is_trusted,
        last_used_at=device.last_used_at,
        created_at=device.created_at,
    )


# -- Routes --


@app.post("/devices", response_model=schemas.DeviceResponse, status_code=201)
async def register_device(
    body: schemas.RegisterDeviceRequest,
    request: Request,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new device for the authenticated user.

    If the same device_id already exists for this user, returns 409 Conflict.
    """
    repo = repository.DeviceRepository(db)

    # Check for duplicate device_id for this user
    existing = await repo.get_device_by_device_id(user.sub, body.device_id)
    if existing:
        raise conflict(f"Device '{body.device_id}' is already registered")

    device = await repo.register_device(
        user_id=user.sub,
        device_id=body.device_id,
        device_name=body.device_name,
        device_type=body.device_type,
        os=body.os,
        browser=body.browser,
        fingerprint=body.fingerprint,
        ip_address=request.client.host if request.client else None,
    )
    return _device_response(device)


@app.get("/devices", response_model=list[schemas.DeviceResponse])
async def list_devices(
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all devices belonging to the authenticated user."""
    repo = repository.DeviceRepository(db)
    devices = await repo.list_user_devices(user.sub)
    return [_device_response(d) for d in devices]


@app.get("/devices/{device_id}", response_model=schemas.DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get device details by primary key UUID."""
    repo = repository.DeviceRepository(db)
    device = await repo.get_device_by_id(device_id)
    if not device:
        raise not_found("Device", device_id)
    return _device_response(device)


@app.put("/devices/{device_id}/trust", response_model=schemas.DeviceResponse)
async def trust_device(
    device_id: str,
    body: schemas.TrustDeviceRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a device as trusted or untrusted.

    Only the device owner can change trust status.
    """
    repo = repository.DeviceRepository(db)
    device = await repo.get_device_by_id(device_id)
    if not device:
        raise not_found("Device", device_id)

    # Only the owner can trust/untrust their own device
    if str(device.user_id) != user.sub:
        raise forbidden("You can only manage your own devices")

    updated = await repo.update_trust(device_id, body.is_trusted)
    return _device_response(updated)


@app.delete("/devices/{device_id}", status_code=204)
async def delete_device(
    device_id: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a device. Only the device owner can delete it."""
    repo = repository.DeviceRepository(db)
    device = await repo.get_device_by_id(device_id)
    if not device:
        raise not_found("Device", device_id)

    if str(device.user_id) != user.sub:
        raise forbidden("You can only delete your own devices")

    await repo.delete_device(device_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=device_config.settings.service_port,
        reload=device_config.settings.debug,
    )
