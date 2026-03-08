"""
Ride Feedback Service — FastAPI application.

ROUTES:
  POST /feedback                — Submit feedback for a trip
  GET  /trips/{id}/feedback     — Get feedback for a trip
  GET  /riders/{id}/feedback    — Get feedback submitted by a rider
  GET  /drivers/{id}/feedback   — Get feedback for a driver
  GET  /health                  — Health check
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
    title="Ride Feedback Service",
    version="0.1.0",
    description="Ride feedback and ratings",
    lifespan=lifespan,
)


@app.post("/feedback", response_model=schemas.FeedbackResponse, status_code=201)
async def create_feedback(
    body: schemas.CreateFeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.RideFeedbackRepository(db)
    fb = await repo.create_feedback(
        trip_id=body.trip_id,
        rider_id=body.rider_id,
        driver_id=body.driver_id,
        rating=body.rating,
        comment=body.comment,
        feedback_type=body.feedback_type,
    )
    return _fb_response(fb)


@app.get("/trips/{trip_id}/feedback", response_model=schemas.FeedbackListResponse)
async def get_trip_feedback(trip_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RideFeedbackRepository(db)
    items = await repo.get_feedback_for_trip(trip_id)
    avg = sum(f.rating for f in items) / len(items) if items else None
    return schemas.FeedbackListResponse(
        feedback=[_fb_response(f) for f in items],
        count=len(items),
        average_rating=avg,
    )


@app.get("/riders/{rider_id}/feedback", response_model=schemas.FeedbackListResponse)
async def get_rider_feedback(rider_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RideFeedbackRepository(db)
    items = await repo.get_feedback_by_rider(rider_id)
    return schemas.FeedbackListResponse(
        feedback=[_fb_response(f) for f in items],
        count=len(items),
    )


@app.get("/drivers/{driver_id}/feedback", response_model=schemas.FeedbackListResponse)
async def get_driver_feedback(driver_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.RideFeedbackRepository(db)
    items = await repo.get_feedback_for_driver(driver_id)
    avg = sum(f.rating for f in items) / len(items) if items else None
    return schemas.FeedbackListResponse(
        feedback=[_fb_response(f) for f in items],
        count=len(items),
        average_rating=avg,
    )


def _fb_response(fb) -> schemas.FeedbackResponse:
    return schemas.FeedbackResponse(
        id=str(fb.id),
        trip_id=str(fb.trip_id),
        rider_id=str(fb.rider_id),
        driver_id=str(fb.driver_id),
        rating=fb.rating,
        comment=fb.comment,
        feedback_type=fb.feedback_type,
        created_at=fb.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=svc_config.settings.service_port, reload=svc_config.settings.debug)
