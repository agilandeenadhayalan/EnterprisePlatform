"""
Driver earnings service repository — database access layer.
"""

from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import models


class EarningsRepository:
    """Database operations for the driver earnings service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_earnings(
        self,
        driver_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[models.DriverEarningModel]:
        """Get earnings for a driver."""
        result = await self.db.execute(
            select(models.DriverEarningModel)
            .where(models.DriverEarningModel.driver_id == driver_id)
            .order_by(models.DriverEarningModel.earning_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_earnings(self, driver_id: str) -> int:
        """Count total earnings records for a driver."""
        result = await self.db.execute(
            select(func.count())
            .select_from(models.DriverEarningModel)
            .where(models.DriverEarningModel.driver_id == driver_id)
        )
        return result.scalar() or 0

    async def get_daily_earnings(
        self,
        driver_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Get daily aggregated earnings for a driver."""
        query = (
            select(
                models.DriverEarningModel.earning_date,
                func.sum(models.DriverEarningModel.amount).label("total_amount"),
                func.count().label("trip_count"),
            )
            .where(models.DriverEarningModel.driver_id == driver_id)
            .group_by(models.DriverEarningModel.earning_date)
            .order_by(models.DriverEarningModel.earning_date.desc())
        )
        if start_date:
            query = query.where(models.DriverEarningModel.earning_date >= start_date)
        if end_date:
            query = query.where(models.DriverEarningModel.earning_date <= end_date)

        result = await self.db.execute(query)
        return [
            {"date": row.earning_date, "total_amount": float(row.total_amount), "trip_count": row.trip_count}
            for row in result
        ]

    async def get_earnings_summary(self, driver_id: str) -> dict:
        """Get earnings summary for a driver."""
        result = await self.db.execute(
            select(
                func.sum(models.DriverEarningModel.amount).label("total"),
                func.count().label("count"),
            )
            .where(models.DriverEarningModel.driver_id == driver_id)
        )
        row = result.one()
        total = float(row.total) if row.total else 0.0
        count = row.count or 0
        avg = round(total / count, 2) if count > 0 else 0.0
        return {"total_earnings": total, "total_trips": count, "average_per_trip": avg}
