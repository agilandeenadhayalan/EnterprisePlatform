"""
Subscription service repository — database access layer.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import SubscriptionModel


# Available plans
PLANS = [
    {
        "id": "basic",
        "name": "Basic",
        "price_per_month": 9.99,
        "description": "Essential features for occasional riders",
        "features": ["Priority booking", "Email support", "Ride history"],
    },
    {
        "id": "premium",
        "name": "Premium",
        "price_per_month": 19.99,
        "description": "Enhanced features for daily commuters",
        "features": ["Priority booking", "24/7 support", "Ride history", "Ride discounts (10%)", "Free cancellations"],
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price_per_month": 49.99,
        "description": "Full platform access for business users",
        "features": ["Priority booking", "Dedicated support", "Ride history", "Ride discounts (20%)", "Free cancellations", "Fleet management", "Analytics dashboard"],
    },
]


class SubscriptionRepository:
    """Database operations for the subscription service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
    ) -> SubscriptionModel:
        """Create a new subscription."""
        plan = next((p for p in PLANS if p["id"] == plan_id), None)
        price = plan["price_per_month"] if plan else 0
        sub = SubscriptionModel(
            user_id=user_id,
            plan_id=plan_id,
            price_per_month=price,
        )
        self.db.add(sub)
        await self.db.flush()
        return sub

    async def get_subscription(self, subscription_id: str) -> Optional[SubscriptionModel]:
        """Get a subscription by ID."""
        result = await self.db.execute(
            select(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def get_user_subscription(self, user_id: str) -> Optional[SubscriptionModel]:
        """Get active subscription for a user."""
        result = await self.db.execute(
            select(SubscriptionModel)
            .where(
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.status == "active",
            )
            .order_by(SubscriptionModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def cancel_subscription(self, subscription_id: str) -> Optional[SubscriptionModel]:
        """Cancel a subscription."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(SubscriptionModel)
            .where(SubscriptionModel.id == subscription_id)
            .values(status="cancelled", cancelled_at=now, updated_at=now)
        )
        return await self.get_subscription(subscription_id)

    def get_plans(self) -> List[Dict]:
        """Get available subscription plans."""
        return PLANS
