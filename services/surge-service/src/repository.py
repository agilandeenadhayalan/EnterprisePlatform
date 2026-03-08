"""
Surge service repository — database access layer.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import SurgeZoneModel


class SurgeRepository:
    """Database operations for the surge service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_zone(self, zone_id: str) -> Optional[SurgeZoneModel]:
        """Find a surge zone by its zone_id."""
        result = await self.db.execute(
            select(SurgeZoneModel).where(SurgeZoneModel.zone_id == zone_id)
        )
        return result.scalar_one_or_none()

    async def update_zone(
        self, zone_id: str, surge_multiplier: float,
        demand_count: Optional[int] = None, supply_count: Optional[int] = None,
    ) -> Optional[SurgeZoneModel]:
        """Update surge multiplier and optionally demand/supply counts."""
        values = {
            "surge_multiplier": surge_multiplier,
            "last_calculated_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        if demand_count is not None:
            values["demand_count"] = demand_count
        if supply_count is not None:
            values["supply_count"] = supply_count

        await self.db.execute(
            update(SurgeZoneModel)
            .where(SurgeZoneModel.zone_id == zone_id)
            .values(**values)
        )
        return await self.get_zone(zone_id)

    async def list_active_zones(self) -> list[SurgeZoneModel]:
        """List zones with active surge (multiplier > 1.0)."""
        result = await self.db.execute(
            select(SurgeZoneModel).where(
                SurgeZoneModel.is_active == True,
                SurgeZoneModel.surge_multiplier > 1.0,
            )
        )
        return list(result.scalars().all())
