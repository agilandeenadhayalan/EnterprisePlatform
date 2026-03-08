"""
Trip service repository — database access layer.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import TripModel


VALID_STATUSES = [
    "requested", "driver_assigned", "driver_en_route",
    "arrived", "in_progress", "completed", "cancelled",
]

VALID_TRANSITIONS = {
    "requested": ["driver_assigned", "cancelled"],
    "driver_assigned": ["driver_en_route", "cancelled"],
    "driver_en_route": ["arrived", "cancelled"],
    "arrived": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}


class TripRepository:
    """Database operations for the trip service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_trip(
        self,
        rider_id: str,
        pickup_latitude: float,
        pickup_longitude: float,
        dropoff_latitude: float,
        dropoff_longitude: float,
        pickup_address: Optional[str] = None,
        dropoff_address: Optional[str] = None,
        vehicle_type: Optional[str] = None,
    ) -> TripModel:
        """Create a new trip with status 'requested'."""
        trip = TripModel(
            rider_id=rider_id,
            pickup_latitude=pickup_latitude,
            pickup_longitude=pickup_longitude,
            pickup_address=pickup_address,
            dropoff_latitude=dropoff_latitude,
            dropoff_longitude=dropoff_longitude,
            dropoff_address=dropoff_address,
            vehicle_type=vehicle_type,
            status="requested",
        )
        self.db.add(trip)
        await self.db.flush()
        return trip

    async def get_trip_by_id(self, trip_id: str) -> Optional[TripModel]:
        """Find a trip by UUID."""
        result = await self.db.execute(
            select(TripModel).where(TripModel.id == trip_id)
        )
        return result.scalar_one_or_none()

    async def update_trip_status(
        self,
        trip_id: str,
        new_status: str,
        driver_id: Optional[str] = None,
        vehicle_id: Optional[str] = None,
    ) -> Optional[TripModel]:
        """Update a trip's status and optionally assign driver/vehicle."""
        values = {
            "status": new_status,
            "updated_at": datetime.now(timezone.utc),
        }
        if driver_id:
            values["driver_id"] = driver_id
        if vehicle_id:
            values["vehicle_id"] = vehicle_id
        if new_status == "in_progress":
            values["started_at"] = datetime.now(timezone.utc)
        elif new_status == "completed":
            values["completed_at"] = datetime.now(timezone.utc)
        elif new_status == "cancelled":
            values["cancelled_at"] = datetime.now(timezone.utc)

        await self.db.execute(
            update(TripModel)
            .where(TripModel.id == trip_id)
            .values(**values)
        )
        return await self.get_trip_by_id(trip_id)

    async def list_trips(
        self,
        status: Optional[str] = None,
        rider_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TripModel]:
        """List trips with optional filters."""
        query = select(TripModel)
        if status:
            query = query.where(TripModel.status == status)
        if rider_id:
            query = query.where(TripModel.rider_id == rider_id)
        query = query.order_by(TripModel.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_rider_trips(self, rider_id: str) -> list[TripModel]:
        """Get all trips for a specific rider."""
        result = await self.db.execute(
            select(TripModel)
            .where(TripModel.rider_id == rider_id)
            .order_by(TripModel.created_at.desc())
        )
        return list(result.scalars().all())
