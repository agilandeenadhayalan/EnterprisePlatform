"""
Driver rating service repository — database access layer.
"""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import models


class RatingRepository:
    """Database operations for the driver rating service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_rating(self, **fields) -> models.DriverRatingModel:
        """Insert a new rating record."""
        rating = models.DriverRatingModel(**fields)
        self.db.add(rating)
        await self.db.flush()
        return rating

    async def get_driver_ratings(
        self,
        driver_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[models.DriverRatingModel]:
        """Get ratings for a driver."""
        result = await self.db.execute(
            select(models.DriverRatingModel)
            .where(models.DriverRatingModel.driver_id == driver_id)
            .order_by(models.DriverRatingModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_driver_ratings(self, driver_id: str) -> int:
        """Count total ratings for a driver."""
        result = await self.db.execute(
            select(func.count())
            .select_from(models.DriverRatingModel)
            .where(models.DriverRatingModel.driver_id == driver_id)
        )
        return result.scalar() or 0

    async def get_average_rating(self, driver_id: str) -> float:
        """Calculate average rating for a driver."""
        result = await self.db.execute(
            select(func.avg(models.DriverRatingModel.rating))
            .where(models.DriverRatingModel.driver_id == driver_id)
        )
        avg = result.scalar()
        return round(float(avg), 2) if avg else 0.0

    async def get_rating_distribution(self, driver_id: str) -> dict[str, int]:
        """Get count of each rating value (1-5) for a driver."""
        result = await self.db.execute(
            select(
                models.DriverRatingModel.rating,
                func.count().label("count"),
            )
            .where(models.DriverRatingModel.driver_id == driver_id)
            .group_by(models.DriverRatingModel.rating)
        )
        dist = {str(i): 0 for i in range(1, 6)}
        for row in result:
            dist[str(row.rating)] = row.count
        return dist
