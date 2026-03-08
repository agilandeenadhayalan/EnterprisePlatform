"""
Pricing service repository — database access layer.

Handles pricing rule lookups for fare calculation.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import PricingRuleModel


class PricingRepository:
    """Database operations for the pricing service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_rule_by_vehicle_type(self, vehicle_type: str) -> Optional[PricingRuleModel]:
        """Find the active pricing rule for a vehicle type."""
        result = await self.db.execute(
            select(PricingRuleModel).where(
                PricingRuleModel.vehicle_type == vehicle_type,
                PricingRuleModel.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_rules(self) -> list[PricingRuleModel]:
        """List all active pricing rules."""
        result = await self.db.execute(
            select(PricingRuleModel)
            .where(PricingRuleModel.is_active == True)
            .order_by(PricingRuleModel.vehicle_type)
        )
        return list(result.scalars().all())
