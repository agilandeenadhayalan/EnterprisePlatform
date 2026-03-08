"""Payment method service repository."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models import PaymentMethodModel

class PaymentMethodRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> PaymentMethodModel:
        pm = PaymentMethodModel(**fields)
        self.db.add(pm)
        await self.db.flush()
        return pm

    async def get_by_id(self, pm_id: str) -> Optional[PaymentMethodModel]:
        result = await self.db.execute(select(PaymentMethodModel).where(PaymentMethodModel.id == pm_id))
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[PaymentMethodModel]:
        result = await self.db.execute(
            select(PaymentMethodModel).where(PaymentMethodModel.user_id == user_id, PaymentMethodModel.is_active == True)
            .order_by(PaymentMethodModel.is_default.desc(), PaymentMethodModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_method(self, pm_id: str) -> bool:
        result = await self.db.execute(delete(PaymentMethodModel).where(PaymentMethodModel.id == pm_id))
        return result.rowcount > 0

    async def set_default(self, user_id: str, pm_id: str) -> Optional[PaymentMethodModel]:
        # Unset all defaults for this user
        await self.db.execute(
            update(PaymentMethodModel).where(PaymentMethodModel.user_id == user_id).values(is_default=False)
        )
        # Set the chosen one as default
        await self.db.execute(
            update(PaymentMethodModel).where(PaymentMethodModel.id == pm_id).values(is_default=True, updated_at=datetime.now(timezone.utc))
        )
        return await self.get_by_id(pm_id)
