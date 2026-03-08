"""Refund service repository."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import RefundModel

class RefundRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_refund(self, **fields) -> RefundModel:
        refund = RefundModel(**fields)
        self.db.add(refund)
        await self.db.flush()
        return refund

    async def get_by_id(self, refund_id: str) -> Optional[RefundModel]:
        result = await self.db.execute(select(RefundModel).where(RefundModel.id == refund_id))
        return result.scalar_one_or_none()

    async def list_by_payment(self, payment_id: str) -> list[RefundModel]:
        result = await self.db.execute(
            select(RefundModel).where(RefundModel.payment_id == payment_id).order_by(RefundModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def approve(self, refund_id: str, approved_by: str) -> Optional[RefundModel]:
        await self.db.execute(
            update(RefundModel).where(RefundModel.id == refund_id)
            .values(status="approved", approved_by=approved_by, updated_at=datetime.now(timezone.utc))
        )
        return await self.get_by_id(refund_id)
