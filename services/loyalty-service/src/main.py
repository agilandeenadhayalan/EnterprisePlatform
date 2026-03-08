"""
Loyalty Service — FastAPI application.

ROUTES:
  GET  /loyalty/{user_id}              — Get user's loyalty balance
  POST /loyalty/{user_id}/earn         — Earn loyalty points
  POST /loyalty/{user_id}/redeem       — Redeem loyalty points
  GET  /loyalty/{user_id}/transactions — Get transaction history
  GET  /loyalty/{user_id}/tier         — Get tier information
  GET  /health                         — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, bad_request

import config as service_config
import models  # noqa: F401
import schemas
import repository
from repository import get_next_tier_info


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(service_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Loyalty Service",
    version="0.1.0",
    description="Loyalty points and rewards for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/loyalty/{user_id}", response_model=schemas.LoyaltyBalanceResponse)
async def get_balance(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get user's loyalty balance and tier."""
    repo = repository.LoyaltyRepository(db)
    balance = await repo.get_or_create_balance(user_id)
    return schemas.LoyaltyBalanceResponse(
        user_id=str(balance.user_id),
        total_points=balance.total_points,
        tier=balance.tier,
        lifetime_points=balance.lifetime_points,
    )


@app.post("/loyalty/{user_id}/earn", response_model=schemas.EarnRedeemResponse, status_code=201)
async def earn_points(
    user_id: str,
    body: schemas.EarnPointsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Earn loyalty points."""
    repo = repository.LoyaltyRepository(db)
    balance = await repo.earn_points(
        user_id=user_id,
        points=body.points,
        description=body.description,
        reference_id=body.reference_id,
    )
    return schemas.EarnRedeemResponse(
        user_id=user_id,
        points_changed=body.points,
        new_balance=balance.total_points,
        tier=balance.tier,
        message=f"Earned {body.points} points",
    )


@app.post("/loyalty/{user_id}/redeem", response_model=schemas.EarnRedeemResponse)
async def redeem_points(
    user_id: str,
    body: schemas.RedeemPointsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Redeem loyalty points."""
    repo = repository.LoyaltyRepository(db)
    balance = await repo.redeem_points(
        user_id=user_id,
        points=body.points,
        description=body.description,
        reference_id=body.reference_id,
    )
    if not balance:
        raise bad_request("Insufficient loyalty points")
    return schemas.EarnRedeemResponse(
        user_id=user_id,
        points_changed=-body.points,
        new_balance=balance.total_points,
        tier=balance.tier,
        message=f"Redeemed {body.points} points",
    )


@app.get("/loyalty/{user_id}/transactions", response_model=schemas.LoyaltyTransactionListResponse)
async def get_transactions(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get loyalty transaction history for a user."""
    repo = repository.LoyaltyRepository(db)
    transactions = await repo.get_transactions(user_id)
    return schemas.LoyaltyTransactionListResponse(
        transactions=[
            schemas.LoyaltyTransactionResponse(
                id=str(t.id),
                user_id=str(t.user_id),
                points=t.points,
                transaction_type=t.transaction_type,
                description=t.description,
                reference_id=t.reference_id,
                created_at=t.created_at,
            )
            for t in transactions
        ],
        count=len(transactions),
    )


@app.get("/loyalty/{user_id}/tier", response_model=schemas.LoyaltyTierResponse)
async def get_tier(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get user's tier information."""
    repo = repository.LoyaltyRepository(db)
    balance = await repo.get_or_create_balance(user_id)
    next_tier, points_needed = get_next_tier_info(balance.lifetime_points)
    return schemas.LoyaltyTierResponse(
        user_id=str(balance.user_id),
        tier=balance.tier,
        lifetime_points=balance.lifetime_points,
        next_tier=next_tier,
        points_to_next_tier=points_needed,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
