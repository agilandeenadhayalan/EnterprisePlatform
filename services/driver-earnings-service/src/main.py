"""
Driver Earnings Service — FastAPI application.

ROUTES:
  GET  /drivers/{id}/earnings          — List earnings for a driver
  GET  /drivers/{id}/earnings/daily    — Get daily aggregated earnings
  GET  /drivers/{id}/earnings/summary  — Get earnings summary
  GET  /health                         — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import date

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
    title="Driver Earnings Service",
    version="0.1.0",
    description="Driver earnings tracking and reporting",
    lifespan=lifespan,
)


# -- Routes --


@app.get("/drivers/{driver_id}/earnings", response_model=schemas.EarningListResponse)
async def list_earnings(
    driver_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List earnings for a driver."""
    repo = repository.EarningsRepository(db)
    earnings = await repo.get_earnings(driver_id, skip=skip, limit=limit)
    total = await repo.count_earnings(driver_id)
    return schemas.EarningListResponse(
        earnings=[_earning_response(e) for e in earnings],
        total=total,
    )


@app.get("/drivers/{driver_id}/earnings/daily", response_model=schemas.DailyEarningsListResponse)
async def get_daily_earnings(
    driver_id: str,
    start_date: date = Query(None),
    end_date: date = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get daily aggregated earnings for a driver."""
    repo = repository.EarningsRepository(db)
    daily = await repo.get_daily_earnings(driver_id, start_date=start_date, end_date=end_date)
    return schemas.DailyEarningsListResponse(
        daily_earnings=[
            schemas.DailyEarningResponse(
                date=d["date"],
                total_amount=d["total_amount"],
                trip_count=d["trip_count"],
                currency="USD",
            )
            for d in daily
        ],
        total_days=len(daily),
    )


@app.get("/drivers/{driver_id}/earnings/summary", response_model=schemas.EarningSummaryResponse)
async def get_earnings_summary(
    driver_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get earnings summary for a driver."""
    repo = repository.EarningsRepository(db)
    summary = await repo.get_earnings_summary(driver_id)
    return schemas.EarningSummaryResponse(
        driver_id=driver_id,
        currency="USD",
        **summary,
    )


def _earning_response(earning) -> schemas.EarningResponse:
    return schemas.EarningResponse(
        id=str(earning.id),
        driver_id=str(earning.driver_id),
        trip_id=str(earning.trip_id) if earning.trip_id else None,
        amount=earning.amount,
        currency=earning.currency,
        earning_type=earning.earning_type,
        description=earning.description,
        earning_date=earning.earning_date,
        created_at=earning.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=service_config.settings.service_port, reload=service_config.settings.debug)
