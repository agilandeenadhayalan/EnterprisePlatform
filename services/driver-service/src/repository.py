"""
Driver service repository — database access layer.
"""

import math
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

import models


class DriverRepository:
    """Database operations for the driver service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_driver(self, **fields) -> models.DriverModel:
        """Insert a new driver and return the created record."""
        driver = models.DriverModel(**fields)
        self.db.add(driver)
        await self.db.flush()
        return driver

    async def get_driver_by_id(self, driver_id: str) -> Optional[models.DriverModel]:
        """Find a driver by UUID."""
        result = await self.db.execute(
            select(models.DriverModel).where(models.DriverModel.id == driver_id)
        )
        return result.scalar_one_or_none()

    async def get_driver_by_email(self, email: str) -> Optional[models.DriverModel]:
        """Find a driver by email address."""
        result = await self.db.execute(
            select(models.DriverModel).where(models.DriverModel.email == email)
        )
        return result.scalar_one_or_none()

    async def get_driver_by_user_id(self, user_id: str) -> Optional[models.DriverModel]:
        """Find a driver by associated user ID."""
        result = await self.db.execute(
            select(models.DriverModel).where(models.DriverModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_drivers(self, skip: int = 0, limit: int = 50) -> list[models.DriverModel]:
        """List all drivers with pagination."""
        result = await self.db.execute(
            select(models.DriverModel)
            .order_by(models.DriverModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_drivers(self) -> int:
        """Count total drivers."""
        result = await self.db.execute(
            select(func.count()).select_from(models.DriverModel)
        )
        return result.scalar() or 0

    async def update_driver(self, driver_id: str, **fields) -> Optional[models.DriverModel]:
        """Update specific fields on a driver record."""
        fields["updated_at"] = datetime.utcnow()
        await self.db.execute(
            update(models.DriverModel)
            .where(models.DriverModel.id == driver_id)
            .values(**fields)
        )
        return await self.get_driver_by_id(driver_id)

    async def find_nearby_drivers(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        limit: int = 10,
    ) -> list[models.DriverModel]:
        """
        Find drivers near a given location using Haversine approximation.
        Filters to online and active drivers only.
        """
        # Rough degree-based bounding box for initial filter
        lat_range = radius_km / 111.0
        lon_range = radius_km / (111.0 * max(math.cos(math.radians(latitude)), 0.001))

        result = await self.db.execute(
            select(models.DriverModel)
            .where(
                models.DriverModel.is_active.is_(True),
                models.DriverModel.status == "online",
                models.DriverModel.latitude.isnot(None),
                models.DriverModel.longitude.isnot(None),
                models.DriverModel.latitude.between(latitude - lat_range, latitude + lat_range),
                models.DriverModel.longitude.between(longitude - lon_range, longitude + lon_range),
            )
            .limit(limit)
        )
        return list(result.scalars().all())
