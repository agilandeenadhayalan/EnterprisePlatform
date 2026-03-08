"""
Driver Rating Service — FastAPI application.

ROUTES:
  POST /ratings                       — Submit a rating for a driver
  GET  /drivers/{id}/ratings          — List ratings for a driver
  GET  /drivers/{id}/rating/summary   — Get rating summary (avg, distribution)
  GET  /health                        — Health check (provided by create_app)
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
    title="Driver Rating Service",
    version="0.1.0",
    description="Driver ratings and reviews management",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/ratings", response_model=schemas.RatingResponse, status_code=201)
async def create_rating(
    body: schemas.RatingCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a rating for a driver."""
    repo = repository.RatingRepository(db)
    rating = await repo.create_rating(**body.model_dump())
    return _rating_response(rating)


@app.get("/drivers/{driver_id}/ratings", response_model=schemas.RatingListResponse)
async def list_ratings(
    driver_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List ratings for a driver."""
    repo = repository.RatingRepository(db)
    ratings = await repo.get_driver_ratings(driver_id, skip=skip, limit=limit)
    total = await repo.count_driver_ratings(driver_id)
    return schemas.RatingListResponse(
        ratings=[_rating_response(r) for r in ratings],
        total=total,
    )


@app.get("/drivers/{driver_id}/rating/summary", response_model=schemas.RatingSummaryResponse)
async def get_rating_summary(
    driver_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get rating summary for a driver."""
    repo = repository.RatingRepository(db)
    avg = await repo.get_average_rating(driver_id)
    total = await repo.count_driver_ratings(driver_id)
    dist = await repo.get_rating_distribution(driver_id)
    return schemas.RatingSummaryResponse(
        driver_id=driver_id,
        average_rating=avg,
        total_ratings=total,
        rating_distribution=dist,
    )


def _rating_response(rating) -> schemas.RatingResponse:
    return schemas.RatingResponse(
        id=str(rating.id),
        driver_id=str(rating.driver_id),
        rider_id=str(rating.rider_id),
        trip_id=str(rating.trip_id),
        rating=rating.rating,
        comment=rating.comment,
        created_at=rating.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=service_config.settings.service_port, reload=service_config.settings.debug)
