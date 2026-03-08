"""
Address Service — FastAPI application.

ROUTES:
  POST   /addresses                      — Add address (requires auth)
  GET    /addresses                      — List user's addresses (requires auth)
  GET    /addresses/{address_id}         — Get address
  PUT    /addresses/{address_id}         — Update address (owner only)
  DELETE /addresses/{address_id}         — Remove address (owner only)
  PUT    /addresses/{address_id}/default — Set as default address
  GET    /health                         — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, forbidden
from mobility_common.fastapi.middleware import get_current_user, TokenPayload

import config as address_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(address_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Address Service",
    version="0.1.0",
    description="Address management for Smart Mobility Platform — add, list, update, remove addresses",
    lifespan=lifespan,
)


# -- Helper --

def _address_response(address) -> schemas.AddressResponse:
    """Convert an AddressModel to an AddressResponse."""
    return schemas.AddressResponse(
        id=str(address.id),
        user_id=str(address.user_id),
        label=address.label,
        line1=address.line1,
        line2=address.line2,
        city=address.city,
        state=address.state,
        postal_code=address.postal_code,
        country=address.country,
        latitude=address.latitude,
        longitude=address.longitude,
        is_default=address.is_default,
        created_at=address.created_at,
        updated_at=address.updated_at,
    )


# -- Routes --


@app.post("/addresses", response_model=schemas.AddressResponse, status_code=201)
async def create_address(
    body: schemas.CreateAddressRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new address for the authenticated user."""
    repo = repository.AddressRepository(db)

    # If this is marked as default, clear other defaults first
    if body.is_default:
        await repo.clear_default(user.sub)

    address_data = body.model_dump()
    address = await repo.create_address(user_id=user.sub, **address_data)
    return _address_response(address)


@app.get("/addresses", response_model=list[schemas.AddressResponse])
async def list_addresses(
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all addresses belonging to the authenticated user."""
    repo = repository.AddressRepository(db)
    addresses = await repo.list_user_addresses(user.sub)
    return [_address_response(a) for a in addresses]


@app.get("/addresses/{address_id}", response_model=schemas.AddressResponse)
async def get_address(
    address_id: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific address by ID."""
    repo = repository.AddressRepository(db)
    address = await repo.get_address_by_id(address_id)
    if not address:
        raise not_found("Address", address_id)
    return _address_response(address)


@app.put("/addresses/{address_id}", response_model=schemas.AddressResponse)
async def update_address(
    address_id: str,
    body: schemas.UpdateAddressRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an address. Only the address owner can update it."""
    repo = repository.AddressRepository(db)
    address = await repo.get_address_by_id(address_id)
    if not address:
        raise not_found("Address", address_id)

    if str(address.user_id) != user.sub:
        raise forbidden("You can only update your own addresses")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return _address_response(address)

    updated = await repo.update_address(address_id, **update_data)
    return _address_response(updated)


@app.delete("/addresses/{address_id}", status_code=204)
async def delete_address(
    address_id: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an address. Only the address owner can delete it."""
    repo = repository.AddressRepository(db)
    address = await repo.get_address_by_id(address_id)
    if not address:
        raise not_found("Address", address_id)

    if str(address.user_id) != user.sub:
        raise forbidden("You can only delete your own addresses")

    await repo.delete_address(address_id)


@app.put("/addresses/{address_id}/default", response_model=schemas.AddressResponse)
async def set_default_address(
    address_id: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set an address as the default for the authenticated user."""
    repo = repository.AddressRepository(db)
    address = await repo.get_address_by_id(address_id)
    if not address:
        raise not_found("Address", address_id)

    if str(address.user_id) != user.sub:
        raise forbidden("You can only manage your own addresses")

    updated = await repo.set_default(address_id, user.sub)
    return _address_response(updated)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=address_config.settings.service_port,
        reload=address_config.settings.debug,
    )
