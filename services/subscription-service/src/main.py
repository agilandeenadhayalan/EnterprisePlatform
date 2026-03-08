"""
Subscription Service — FastAPI application.

ROUTES:
  POST  /subscriptions            — Create a new subscription
  GET   /subscriptions/{id}       — Get a subscription by ID
  GET   /users/{id}/subscription  — Get active subscription for a user
  PATCH /subscriptions/{id}/cancel — Cancel a subscription
  GET   /plans                     — List available plans
  GET   /health                    — Health check (provided by create_app)
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
from mobility_common.fastapi.errors import not_found

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
    title="Subscription Service",
    version="0.1.0",
    description="Subscription plan management for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/subscriptions", response_model=schemas.SubscriptionResponse, status_code=201)
async def create_subscription(
    body: schemas.CreateSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new subscription."""
    repo = repository.SubscriptionRepository(db)
    sub = await repo.create_subscription(
        user_id=body.user_id,
        plan_id=body.plan_id,
    )
    return schemas.SubscriptionResponse(
        id=str(sub.id),
        user_id=str(sub.user_id),
        plan_id=sub.plan_id,
        status=sub.status,
        price_per_month=float(sub.price_per_month),
        started_at=sub.started_at,
        expires_at=sub.expires_at,
        cancelled_at=sub.cancelled_at,
        created_at=sub.created_at,
    )


@app.get("/subscriptions/{subscription_id}", response_model=schemas.SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a subscription by ID."""
    repo = repository.SubscriptionRepository(db)
    sub = await repo.get_subscription(subscription_id)
    if not sub:
        raise not_found("Subscription", subscription_id)
    return schemas.SubscriptionResponse(
        id=str(sub.id),
        user_id=str(sub.user_id),
        plan_id=sub.plan_id,
        status=sub.status,
        price_per_month=float(sub.price_per_month),
        started_at=sub.started_at,
        expires_at=sub.expires_at,
        cancelled_at=sub.cancelled_at,
        created_at=sub.created_at,
    )


@app.get("/users/{user_id}/subscription", response_model=schemas.SubscriptionResponse)
async def get_user_subscription(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the active subscription for a user."""
    repo = repository.SubscriptionRepository(db)
    sub = await repo.get_user_subscription(user_id)
    if not sub:
        raise not_found("Active subscription for user", user_id)
    return schemas.SubscriptionResponse(
        id=str(sub.id),
        user_id=str(sub.user_id),
        plan_id=sub.plan_id,
        status=sub.status,
        price_per_month=float(sub.price_per_month),
        started_at=sub.started_at,
        expires_at=sub.expires_at,
        cancelled_at=sub.cancelled_at,
        created_at=sub.created_at,
    )


@app.patch("/subscriptions/{subscription_id}/cancel", response_model=schemas.CancelResponse)
async def cancel_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a subscription."""
    repo = repository.SubscriptionRepository(db)
    sub = await repo.cancel_subscription(subscription_id)
    if not sub:
        raise not_found("Subscription", subscription_id)
    return schemas.CancelResponse(
        id=str(sub.id),
        status=sub.status,
        cancelled_at=sub.cancelled_at,
    )


@app.get("/plans", response_model=schemas.PlanListResponse)
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    """List available subscription plans."""
    repo = repository.SubscriptionRepository(db)
    plans = repo.get_plans()
    return schemas.PlanListResponse(
        plans=[schemas.PlanResponse(**p) for p in plans],
        count=len(plans),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
