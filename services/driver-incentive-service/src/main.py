"""
Driver Incentive Service — FastAPI application.

ROUTES:
  GET  /incentives              — List all incentives
  GET  /incentives/active       — List currently active incentives
  POST /incentives              — Create a new incentive
  GET  /drivers/{id}/incentives — Get incentives available for a driver
  GET  /health                  — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine

import config as service_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(service_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Driver Incentive Service",
    version="0.1.0",
    description="Driver incentive and bonus management",
    lifespan=lifespan,
)


# -- Routes --


@app.get("/incentives", response_model=schemas.IncentiveListResponse)
async def list_incentives(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all incentives."""
    repo = repository.IncentiveRepository(db)
    incentives = await repo.list_incentives(skip=skip, limit=limit)
    total = await repo.count_incentives()
    return schemas.IncentiveListResponse(
        incentives=[_incentive_response(i) for i in incentives],
        total=total,
    )


@app.get("/incentives/active", response_model=schemas.IncentiveListResponse)
async def list_active_incentives(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List currently active incentives."""
    repo = repository.IncentiveRepository(db)
    incentives = await repo.get_active_incentives(skip=skip, limit=limit)
    total = await repo.count_active_incentives()
    return schemas.IncentiveListResponse(
        incentives=[_incentive_response(i) for i in incentives],
        total=total,
    )


@app.post("/incentives", response_model=schemas.IncentiveResponse, status_code=201)
async def create_incentive(
    body: schemas.IncentiveCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new incentive."""
    repo = repository.IncentiveRepository(db)
    incentive = await repo.create_incentive(**body.model_dump())
    return _incentive_response(incentive)


@app.get("/drivers/{driver_id}/incentives", response_model=schemas.IncentiveListResponse)
async def get_driver_incentives(
    driver_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get incentives available for a specific driver."""
    repo = repository.IncentiveRepository(db)
    incentives = await repo.get_driver_incentives(driver_id, skip=skip, limit=limit)
    total = len(incentives)
    return schemas.IncentiveListResponse(
        incentives=[_incentive_response(i) for i in incentives],
        total=total,
    )


def _incentive_response(incentive) -> schemas.IncentiveResponse:
    return schemas.IncentiveResponse(
        id=str(incentive.id),
        title=incentive.title,
        description=incentive.description,
        incentive_type=incentive.incentive_type,
        amount=incentive.amount,
        currency=incentive.currency,
        criteria=incentive.criteria,
        is_active=incentive.is_active,
        starts_at=incentive.starts_at,
        ends_at=incentive.ends_at,
        max_claims=incentive.max_claims,
        current_claims=incentive.current_claims,
        created_at=incentive.created_at,
        updated_at=incentive.updated_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=service_config.settings.service_port, reload=service_config.settings.debug)
