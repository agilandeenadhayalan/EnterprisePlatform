"""
Driver location service repository — database access layer.
"""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import models


class LocationRepository:
    """Database operations for the driver location service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_location(self, **fields) -> models.DriverLocationModel:
        """Insert a new location record."""
        location = models.DriverLocationModel(**fields)
        self.db.add(location)
        await self.db.flush()
        return location

    async def get_latest_location(self, driver_id: str) -> Optional[models.DriverLocationModel]:
        """Get the most recent location for a driver."""
        result = await self.db.execute(
            select(models.DriverLocationModel)
            .where(models.DriverLocationModel.driver_id == driver_id)
            .order_by(models.DriverLocationModel.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_location_history(
        self,
        driver_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[models.DriverLocationModel]:
        """Get location history for a driver, ordered newest first."""
        result = await self.db.execute(
            select(models.DriverLocationModel)
            .where(models.DriverLocationModel.driver_id == driver_id)
            .order_by(models.DriverLocationModel.recorded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_locations(self, driver_id: str) -> int:
        """Count total location records for a driver."""
        result = await self.db.execute(
            select(func.count())
            .select_from(models.DriverLocationModel)
            .where(models.DriverLocationModel.driver_id == driver_id)
        )
        return result.scalar() or 0
