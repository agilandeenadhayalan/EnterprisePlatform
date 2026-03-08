"""Promotion service repository — database access layer."""

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import PromotionModel


class PromotionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_promotion(self, **fields) -> PromotionModel:
        promo = PromotionModel(**fields)
        self.db.add(promo)
        await self.db.flush()
        return promo

    async def get_by_id(self, promo_id: str) -> Optional[PromotionModel]:
        result = await self.db.execute(
            select(PromotionModel).where(PromotionModel.id == promo_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[PromotionModel]:
        result = await self.db.execute(
            select(PromotionModel).order_by(PromotionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active(self) -> list[PromotionModel]:
        result = await self.db.execute(
            select(PromotionModel).where(PromotionModel.is_active == True)
        )
        return list(result.scalars().all())

    async def increment_redemptions(self, promo_id: str) -> None:
        await self.db.execute(
            update(PromotionModel)
            .where(PromotionModel.id == promo_id)
            .values(current_redemptions=PromotionModel.current_redemptions + 1)
        )
