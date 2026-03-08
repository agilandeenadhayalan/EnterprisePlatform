"""
Loyalty service repository — database access layer.
"""

from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import LoyaltyPointsModel, LoyaltyTransactionModel


# Tier thresholds
TIERS = [
    ("bronze", 0),
    ("silver", 1000),
    ("gold", 5000),
    ("platinum", 15000),
    ("diamond", 50000),
]


def calculate_tier(lifetime_points: int) -> str:
    """Determine tier based on lifetime points."""
    tier = "bronze"
    for name, threshold in TIERS:
        if lifetime_points >= threshold:
            tier = name
    return tier


def get_next_tier_info(lifetime_points: int) -> tuple[Optional[str], Optional[int]]:
    """Get next tier name and points needed."""
    for i, (name, threshold) in enumerate(TIERS):
        if lifetime_points < threshold:
            return name, threshold - lifetime_points
    return None, None


class LoyaltyRepository:
    """Database operations for the loyalty service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(self, user_id: str) -> Optional[LoyaltyPointsModel]:
        """Get loyalty balance for a user."""
        result = await self.db.execute(
            select(LoyaltyPointsModel).where(LoyaltyPointsModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_balance(self, user_id: str) -> LoyaltyPointsModel:
        """Get or create loyalty balance for a user."""
        balance = await self.get_balance(user_id)
        if not balance:
            balance = LoyaltyPointsModel(user_id=user_id)
            self.db.add(balance)
            await self.db.flush()
        return balance

    async def earn_points(
        self,
        user_id: str,
        points: int,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> LoyaltyPointsModel:
        """Add points to a user's balance."""
        balance = await self.get_or_create_balance(user_id)
        new_total = balance.total_points + points
        new_lifetime = balance.lifetime_points + points
        new_tier = calculate_tier(new_lifetime)

        await self.db.execute(
            update(LoyaltyPointsModel)
            .where(LoyaltyPointsModel.user_id == user_id)
            .values(total_points=new_total, lifetime_points=new_lifetime, tier=new_tier)
        )

        # Record transaction
        txn = LoyaltyTransactionModel(
            user_id=user_id,
            points=points,
            transaction_type="earn",
            description=description,
            reference_id=reference_id,
        )
        self.db.add(txn)
        await self.db.flush()

        balance.total_points = new_total
        balance.lifetime_points = new_lifetime
        balance.tier = new_tier
        return balance

    async def redeem_points(
        self,
        user_id: str,
        points: int,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> Optional[LoyaltyPointsModel]:
        """Redeem points from a user's balance. Returns None if insufficient."""
        balance = await self.get_or_create_balance(user_id)
        if balance.total_points < points:
            return None

        new_total = balance.total_points - points
        await self.db.execute(
            update(LoyaltyPointsModel)
            .where(LoyaltyPointsModel.user_id == user_id)
            .values(total_points=new_total)
        )

        txn = LoyaltyTransactionModel(
            user_id=user_id,
            points=-points,
            transaction_type="redeem",
            description=description,
            reference_id=reference_id,
        )
        self.db.add(txn)
        await self.db.flush()

        balance.total_points = new_total
        return balance

    async def get_transactions(self, user_id: str, limit: int = 50) -> List[LoyaltyTransactionModel]:
        """Get transaction history for a user."""
        result = await self.db.execute(
            select(LoyaltyTransactionModel)
            .where(LoyaltyTransactionModel.user_id == user_id)
            .order_by(LoyaltyTransactionModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
