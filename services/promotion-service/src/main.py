"""
Promotion Service — FastAPI application.

ROUTES:
  GET  /promotions          — List all promotions
  GET  /promotions/active   — List active promotions
  POST /promotions          — Create a new promotion
  POST /promotions/{id}/redeem — Redeem a promotion
  GET  /health              — Health check
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
from mobility_common.fastapi.errors import not_found, validation_error

import config as promo_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(promo_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Promotion Service",
    version="0.1.0",
    description="Marketing promotions and reward redemption for Smart Mobility Platform",
    lifespan=lifespan,
)


@app.get("/promotions", response_model=schemas.PromotionListResponse)
async def list_promotions(db: AsyncSession = Depends(get_db)):
    repo = repository.PromotionRepository(db)
    promos = await repo.list_all()
    return schemas.PromotionListResponse(
        promotions=[_to_response(p) for p in promos],
        count=len(promos),
    )


@app.get("/promotions/active", response_model=schemas.PromotionListResponse)
async def list_active_promotions(db: AsyncSession = Depends(get_db)):
    repo = repository.PromotionRepository(db)
    promos = await repo.list_active()
    return schemas.PromotionListResponse(
        promotions=[_to_response(p) for p in promos],
        count=len(promos),
    )


@app.post("/promotions", response_model=schemas.PromotionResponse, status_code=201)
async def create_promotion(body: schemas.CreatePromotionRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.PromotionRepository(db)
    promo = await repo.create_promotion(
        title=body.title, description=body.description,
        promotion_type=body.promotion_type, reward_type=body.reward_type,
        reward_value=body.reward_value, max_redemptions=body.max_redemptions,
        start_date=body.start_date, end_date=body.end_date,
    )
    return _to_response(promo)


@app.post("/promotions/{promo_id}/redeem", response_model=schemas.RedeemResponse)
async def redeem_promotion(promo_id: str, body: schemas.RedeemPromotionRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.PromotionRepository(db)
    promo = await repo.get_by_id(promo_id)
    if not promo:
        raise not_found("Promotion", promo_id)
    if not promo.is_active:
        raise validation_error("Promotion is not active")
    if promo.max_redemptions and promo.current_redemptions >= promo.max_redemptions:
        raise validation_error("Promotion redemption limit reached")

    await repo.increment_redemptions(promo_id)
    return schemas.RedeemResponse(
        promotion_id=promo_id, user_id=body.user_id,
        reward_type=promo.reward_type, reward_value=promo.reward_value,
        redeemed=True, message="Promotion redeemed successfully",
    )


def _to_response(p) -> schemas.PromotionResponse:
    return schemas.PromotionResponse(
        id=str(p.id), title=p.title, description=p.description,
        promotion_type=p.promotion_type, reward_type=p.reward_type,
        reward_value=p.reward_value, max_redemptions=p.max_redemptions,
        current_redemptions=p.current_redemptions, is_active=p.is_active,
        start_date=p.start_date, end_date=p.end_date, created_at=p.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=promo_config.settings.service_port, reload=promo_config.settings.debug)
