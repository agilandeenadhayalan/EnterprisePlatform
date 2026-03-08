"""
Driver availability service repository — database access layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

import models


class AvailabilityRepository:
    """Database operations for the driver availability service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_driver_id(self, driver_id: str) -> Optional[models.DriverAvailabilityModel]:
        """Get availability record for a driver."""
        result = await self.db.execute(
            select(models.DriverAvailabilityModel)
            .where(models.DriverAvailabilityModel.driver_id == driver_id)
        )
        return result.scalar_one_or_none()

    async def create_availability(self, **fields) -> models.DriverAvailabilityModel:
        """Create a new availability record."""
        record = models.DriverAvailabilityModel(**fields)
        self.db.add(record)
        await self.db.flush()
        return record

    async def set_online(self, driver_id: str, latitude: float = None, longitude: float = None) -> Optional[models.DriverAvailabilityModel]:
        """Set a driver as online."""
        now = datetime.utcnow()
        existing = await self.get_by_driver_id(driver_id)
        if not existing:
            return await self.create_availability(
                driver_id=driver_id,
                status="online",
                latitude=latitude,
                longitude=longitude,
                last_online_at=now,
            )
        update_fields = {
            "status": "online",
            "last_online_at": now,
            "updated_at": now,
        }
        if latitude is not None:
            update_fields["latitude"] = latitude
        if longitude is not None:
            update_fields["longitude"] = longitude
        await self.db.execute(
            update(models.DriverAvailabilityModel)
            .where(models.DriverAvailabilityModel.driver_id == driver_id)
            .values(**update_fields)
        )
        return await self.get_by_driver_id(driver_id)

    async def set_offline(self, driver_id: str) -> Optional[models.DriverAvailabilityModel]:
        """Set a driver as offline."""
        now = datetime.utcnow()
        existing = await self.get_by_driver_id(driver_id)
        if not existing:
            return await self.create_availability(
                driver_id=driver_id,
                status="offline",
                last_offline_at=now,
            )
        await self.db.execute(
            update(models.DriverAvailabilityModel)
            .where(models.DriverAvailabilityModel.driver_id == driver_id)
            .values(status="offline", last_offline_at=now, updated_at=now)
        )
        return await self.get_by_driver_id(driver_id)

    async def get_available_drivers(self, skip: int = 0, limit: int = 50) -> list[models.DriverAvailabilityModel]:
        """Get all currently online drivers."""
        result = await self.db.execute(
            select(models.DriverAvailabilityModel)
            .where(models.DriverAvailabilityModel.status == "online")
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_available(self) -> int:
        """Count online drivers."""
        result = await self.db.execute(
            select(func.count())
            .select_from(models.DriverAvailabilityModel)
            .where(models.DriverAvailabilityModel.status == "online")
        )
        return result.scalar() or 0
