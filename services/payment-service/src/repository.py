"""Payment service repository — database access layer."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import PaymentModel


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payment(self, **fields) -> PaymentModel:
        payment = PaymentModel(**fields)
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def get_by_id(self, payment_id: str) -> Optional[PaymentModel]:
        result = await self.db.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_trip(self, trip_id: str) -> Optional[PaymentModel]:
        result = await self.db.execute(
            select(PaymentModel).where(PaymentModel.trip_id == trip_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, payment_id: str, status: str, gateway_ref: Optional[str] = None) -> Optional[PaymentModel]:
        values = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if gateway_ref:
            values["payment_gateway_ref"] = gateway_ref
        await self.db.execute(
            update(PaymentModel).where(PaymentModel.id == payment_id).values(**values)
        )
        return await self.get_by_id(payment_id)
