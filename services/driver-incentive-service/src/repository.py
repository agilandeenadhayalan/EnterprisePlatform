"""
Driver incentive service repository — database access layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import models


class IncentiveRepository:
    """Database operations for the driver incentive service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_incentive(self, **fields) -> models.DriverIncentiveModel:
        """Insert a new incentive."""
        incentive = models.DriverIncentiveModel(**fields)
        self.db.add(incentive)
        await self.db.flush()
        return incentive

    async def get_incentive_by_id(self, incentive_id: str) -> Optional[models.DriverIncentiveModel]:
        """Find an incentive by ID."""
        result = await self.db.execute(
            select(models.DriverIncentiveModel)
            .where(models.DriverIncentiveModel.id == incentive_id)
        )
        return result.scalar_one_or_none()

    async def list_incentives(self, skip: int = 0, limit: int = 50) -> list[models.DriverIncentiveModel]:
        """List all incentives with pagination."""
        result = await self.db.execute(
            select(models.DriverIncentiveModel)
            .order_by(models.DriverIncentiveModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_incentives(self) -> int:
        """Count total incentives."""
        result = await self.db.execute(
            select(func.count()).select_from(models.DriverIncentiveModel)
        )
        return result.scalar() or 0

    async def get_active_incentives(self, skip: int = 0, limit: int = 50) -> list[models.DriverIncentiveModel]:
        """Get currently active incentives."""
        now = datetime.utcnow()
        result = await self.db.execute(
            select(models.DriverIncentiveModel)
            .where(
                models.DriverIncentiveModel.is_active.is_(True),
                models.DriverIncentiveModel.starts_at <= now,
                models.DriverIncentiveModel.ends_at >= now,
            )
            .order_by(models.DriverIncentiveModel.ends_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_active_incentives(self) -> int:
        """Count active incentives."""
        now = datetime.utcnow()
        result = await self.db.execute(
            select(func.count())
            .select_from(models.DriverIncentiveModel)
            .where(
                models.DriverIncentiveModel.is_active.is_(True),
                models.DriverIncentiveModel.starts_at <= now,
                models.DriverIncentiveModel.ends_at >= now,
            )
        )
        return result.scalar() or 0

    async def get_driver_incentives(
        self,
        driver_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[models.DriverIncentiveModel]:
        """
        Get incentives available for a specific driver.
        For now, returns all active incentives (driver-specific filtering
        would require a join table for claimed incentives).
        """
        return await self.get_active_incentives(skip=skip, limit=limit)
