"""Discount service repository — database access layer."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import DiscountModel


class DiscountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_code(self, code: str) -> Optional[DiscountModel]:
        result = await self.db.execute(
            select(DiscountModel).where(DiscountModel.code == code)
        )
        return result.scalar_one_or_none()

    async def create_discount(self, **fields) -> DiscountModel:
        discount = DiscountModel(**fields)
        self.db.add(discount)
        await self.db.flush()
        return discount

    async def increment_uses(self, code: str) -> None:
        await self.db.execute(
            update(DiscountModel)
            .where(DiscountModel.code == code)
            .values(current_uses=DiscountModel.current_uses + 1)
        )

    async def list_active(self) -> list[DiscountModel]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(DiscountModel).where(DiscountModel.is_active == True)
        )
        return list(result.scalars().all())
