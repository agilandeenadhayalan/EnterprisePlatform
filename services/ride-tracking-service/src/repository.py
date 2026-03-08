"""Ride tracking repository — database access layer."""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import RideTrackingModel


class RideTrackingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_waypoint(
        self,
        trip_id: str,
        latitude: float,
        longitude: float,
        altitude: Optional[float] = None,
        speed_kmh: Optional[float] = None,
        heading: Optional[float] = None,
        accuracy_meters: Optional[float] = None,
    ) -> RideTrackingModel:
        # Get next sequence number
        result = await self.db.execute(
            select(func.coalesce(func.max(RideTrackingModel.sequence_number), 0))
            .where(RideTrackingModel.trip_id == trip_id)
        )
        next_seq = result.scalar_one() + 1

        waypoint = RideTrackingModel(
            trip_id=trip_id,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            speed_kmh=speed_kmh,
            heading=heading,
            accuracy_meters=accuracy_meters,
            sequence_number=next_seq,
        )
        self.db.add(waypoint)
        await self.db.flush()
        return waypoint

    async def get_track(self, trip_id: str) -> list[RideTrackingModel]:
        result = await self.db.execute(
            select(RideTrackingModel)
            .where(RideTrackingModel.trip_id == trip_id)
            .order_by(RideTrackingModel.sequence_number.asc())
        )
        return list(result.scalars().all())

    async def get_latest_waypoint(self, trip_id: str) -> Optional[RideTrackingModel]:
        result = await self.db.execute(
            select(RideTrackingModel)
            .where(RideTrackingModel.trip_id == trip_id)
            .order_by(RideTrackingModel.sequence_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
