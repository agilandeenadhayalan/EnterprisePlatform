"""
Recommendation Service — FastAPI application.

Collaborative + content-based hybrid recommendations for drivers
and riders. Supports popular zones, similar driver finding,
and cold-start recommendations for new users.

ROUTES:
  POST /recommendations/driver/{driver_id}          — Get zone recommendations for a driver
  POST /recommendations/rider/{rider_id}            — Get route/zone recommendations for a rider
  GET  /recommendations/popular-zones               — Popular pickup zones
  POST /recommendations/similar-drivers/{driver_id} — Find similar drivers
  POST /recommendations/cold-start                  — Recommendations for new users
  GET  /health                                      — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Collaborative + content-based hybrid recommendations",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/recommendations/driver/{driver_id}", response_model=schemas.RecommendationResponse)
async def driver_recommendations(driver_id: str):
    """Get zone recommendations for a driver using hybrid approach."""
    rec = repository.repo.recommend_for_driver(driver_id)
    return schemas.RecommendationResponse(**rec.to_dict())


@app.post("/recommendations/rider/{rider_id}", response_model=schemas.RecommendationResponse)
async def rider_recommendations(rider_id: str):
    """Get zone recommendations for a rider."""
    rec = repository.repo.recommend_for_rider(rider_id)
    return schemas.RecommendationResponse(**rec.to_dict())


@app.get("/recommendations/popular-zones", response_model=schemas.PopularZonesResponse)
async def popular_zones(
    hour: Optional[int] = Query(default=None, description="Hour of day (0-23)"),
    day: Optional[int] = Query(default=None, description="Day of week (0-6)"),
):
    """Get popular pickup zones."""
    zones = repository.repo.get_popular_zones(hour=hour, day=day)
    return schemas.PopularZonesResponse(
        zones=[schemas.PopularZone(**z) for z in zones],
        hour=hour,
        day=day,
        total=len(zones),
    )


@app.post("/recommendations/similar-drivers/{driver_id}", response_model=schemas.SimilarDriversResponse)
async def similar_drivers(driver_id: str):
    """Find drivers with similar ride patterns."""
    similar = repository.repo.find_similar_drivers(driver_id)
    return schemas.SimilarDriversResponse(
        driver_id=driver_id,
        similar_drivers=[schemas.SimilarEntityResponse(**s.to_dict()) for s in similar],
        total=len(similar),
    )


@app.post("/recommendations/cold-start", response_model=schemas.RecommendationResponse)
async def cold_start(req: schemas.ColdStartRequest):
    """Get recommendations for new users with no history."""
    rec = repository.repo.cold_start_recommend(
        user_type=req.user_type,
        preferences=req.initial_preferences if req.initial_preferences else None,
    )
    return schemas.RecommendationResponse(**rec.to_dict())
