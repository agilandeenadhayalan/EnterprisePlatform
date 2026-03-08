"""Ride history repository — read-only database access layer."""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import TripModel


class RideHistoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_rider_history(
        self, rider_id: str, limit: int = 50, offset: int = 0,
    ) -> list[TripModel]:
        result = await self.db.execute(
            select(TripModel)
            .where(
                TripModel.rider_id == rider_id,
                TripModel.status.in_(["completed", "cancelled"]),
            )
            .order_by(TripModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_rider_stats(self, rider_id: str) -> dict:
        result = await self.db.execute(
            select(
                func.count(TripModel.id).label("total_trips"),
                func.count(TripModel.id).filter(TripModel.status == "completed").label("completed_trips"),
                func.count(TripModel.id).filter(TripModel.status == "cancelled").label("cancelled_trips"),
                func.coalesce(func.sum(TripModel.fare_amount), 0).label("total_spent"),
                func.avg(TripModel.fare_amount).label("average_fare"),
            )
            .where(TripModel.rider_id == rider_id)
        )
        row = result.one()
        return {
            "total_trips": row.total_trips,
            "completed_trips": row.completed_trips,
            "cancelled_trips": row.cancelled_trips,
            "total_spent": float(row.total_spent),
            "average_fare": float(row.average_fare) if row.average_fare else None,
        }

    async def get_recent_completed(self, limit: int = 20) -> list[TripModel]:
        result = await self.db.execute(
            select(TripModel)
            .where(TripModel.status == "completed")
            .order_by(TripModel.completed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
