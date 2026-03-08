"""Ride feedback repository — database access layer."""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import RideFeedbackModel


class RideFeedbackRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_feedback(
        self,
        trip_id: str,
        rider_id: str,
        driver_id: str,
        rating: int,
        comment: Optional[str] = None,
        feedback_type: str = "rider_to_driver",
    ) -> RideFeedbackModel:
        feedback = RideFeedbackModel(
            trip_id=trip_id,
            rider_id=rider_id,
            driver_id=driver_id,
            rating=rating,
            comment=comment,
            feedback_type=feedback_type,
        )
        self.db.add(feedback)
        await self.db.flush()
        return feedback

    async def get_feedback_for_trip(self, trip_id: str) -> list[RideFeedbackModel]:
        result = await self.db.execute(
            select(RideFeedbackModel)
            .where(RideFeedbackModel.trip_id == trip_id)
            .order_by(RideFeedbackModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_feedback_by_rider(self, rider_id: str) -> list[RideFeedbackModel]:
        result = await self.db.execute(
            select(RideFeedbackModel)
            .where(RideFeedbackModel.rider_id == rider_id)
            .order_by(RideFeedbackModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_feedback_for_driver(self, driver_id: str) -> list[RideFeedbackModel]:
        result = await self.db.execute(
            select(RideFeedbackModel)
            .where(RideFeedbackModel.driver_id == driver_id)
            .order_by(RideFeedbackModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_driver_average_rating(self, driver_id: str) -> Optional[float]:
        result = await self.db.execute(
            select(func.avg(RideFeedbackModel.rating))
            .where(RideFeedbackModel.driver_id == driver_id)
        )
        return result.scalar_one_or_none()
