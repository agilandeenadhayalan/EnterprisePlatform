"""Payout service repository."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import PayoutModel

class PayoutRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payout(self, **fields) -> PayoutModel:
        payout = PayoutModel(**fields)
        self.db.add(payout)
        await self.db.flush()
        return payout

    async def get_by_id(self, payout_id: str) -> Optional[PayoutModel]:
        result = await self.db.execute(select(PayoutModel).where(PayoutModel.id == payout_id))
        return result.scalar_one_or_none()

    async def list_by_driver(self, driver_id: str) -> list[PayoutModel]:
        result = await self.db.execute(
            select(PayoutModel).where(PayoutModel.driver_id == driver_id).order_by(PayoutModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_pending(self) -> list[PayoutModel]:
        result = await self.db.execute(
            select(PayoutModel).where(PayoutModel.status == "pending").order_by(PayoutModel.created_at)
        )
        return list(result.scalars().all())
