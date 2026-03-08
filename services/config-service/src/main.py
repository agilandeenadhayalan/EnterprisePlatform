"""
Config Service — FastAPI application.

ROUTES:
  GET    /configs                 — List all configurations (admin only, ?service= filter)
  GET    /configs/{service}/{key} — Get a specific config value (authenticated)
  PUT    /configs/{service}/{key} — Set a config value (admin only, increments version)
  DELETE /configs/{service}/{key} — Delete a config entry (admin only)
  GET    /configs/{service}       — Get all configs for a service (authenticated)
  GET    /health                  — Health check (provided by create_app)

Configuration is VERSIONED — every update increments the version number, so
downstream services can detect config changes by comparing versions.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found
from mobility_common.fastapi.middleware import get_current_user, require_role, TokenPayload

import config as cfg_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(cfg_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Config Service",
    version="0.1.0",
    description="Versioned configuration management for Smart Mobility Platform services",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/configs", response_model=schemas.ConfigListResponse)
async def list_configs(
    service: str | None = Query(None, description="Filter by service name"),
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all configurations. Admin only. Supports optional ?service= filter."""
    repo = repository.ConfigRepository(db)
    configs = await repo.list_all(service_filter=service)

    config_list = [
        schemas.ConfigResponse(
            service=c.service,
            key=c.key,
            value=c.value,
            description=c.description,
            version=c.version,
            updated_at=c.updated_at,
        )
        for c in configs
    ]
    return schemas.ConfigListResponse(configs=config_list, count=len(config_list))


@app.get("/configs/{service}/{key}", response_model=schemas.ConfigResponse)
async def get_config(
    service: str,
    key: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific configuration value. Any authenticated user can read configs."""
    repo = repository.ConfigRepository(db)
    config = await repo.get_by_service_key(service, key)

    if not config:
        raise not_found("Configuration", f"{service}/{key}")

    return schemas.ConfigResponse(
        service=config.service,
        key=config.key,
        value=config.value,
        description=config.description,
        version=config.version,
        updated_at=config.updated_at,
    )


@app.put("/configs/{service}/{key}", response_model=schemas.ConfigResponse)
async def set_config(
    service: str,
    key: str,
    body: schemas.SetConfigRequest,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Set or update a configuration value. Admin only.

    If the config already exists, the version is incremented automatically.
    If it doesn't exist, a new entry is created with version=1.
    """
    repo = repository.ConfigRepository(db)
    config = await repo.set_config(
        service=service,
        key=key,
        value=body.value,
        description=body.description,
        updated_by=admin.sub,
    )

    return schemas.ConfigResponse(
        service=config.service,
        key=config.key,
        value=config.value,
        description=config.description,
        version=config.version,
        updated_at=config.updated_at,
    )


@app.delete("/configs/{service}/{key}", status_code=204)
async def delete_config(
    service: str,
    key: str,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a config entry. Admin only."""
    repo = repository.ConfigRepository(db)
    deleted = await repo.delete_config(service, key)
    if not deleted:
        raise not_found("Configuration", f"{service}/{key}")


@app.get("/configs/{service}", response_model=schemas.ConfigListResponse)
async def get_service_configs(
    service: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all configs for a specific service. Any authenticated user can read."""
    repo = repository.ConfigRepository(db)
    configs = await repo.get_by_service(service)

    config_list = [
        schemas.ConfigResponse(
            service=c.service,
            key=c.key,
            value=c.value,
            description=c.description,
            version=c.version,
            updated_at=c.updated_at,
        )
        for c in configs
    ]
    return schemas.ConfigListResponse(configs=config_list, count=len(config_list))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=cfg_config.settings.service_port,
        reload=cfg_config.settings.debug,
    )
