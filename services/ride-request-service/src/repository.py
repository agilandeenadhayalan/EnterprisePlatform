"""
Ride request repository — database access layer.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import RideRequestModel


class RideRequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(
        self,
        rider_id: str,
        pickup_latitude: float,
        pickup_longitude: float,
        dropoff_latitude: float,
        dropoff_longitude: float,
        pickup_address: Optional[str] = None,
        dropoff_address: Optional[str] = None,
        vehicle_type: Optional[str] = None,
    ) -> RideRequestModel:
        request = RideRequestModel(
            rider_id=rider_id,
            pickup_latitude=pickup_latitude,
            pickup_longitude=pickup_longitude,
            pickup_address=pickup_address,
            dropoff_latitude=dropoff_latitude,
            dropoff_longitude=dropoff_longitude,
            dropoff_address=dropoff_address,
            vehicle_type=vehicle_type,
            status="pending",
        )
        self.db.add(request)
        await self.db.flush()
        return request

    async def get_request_by_id(self, request_id: str) -> Optional[RideRequestModel]:
        result = await self.db.execute(
            select(RideRequestModel).where(RideRequestModel.id == request_id)
        )
        return result.scalar_one_or_none()

    async def cancel_request(self, request_id: str) -> bool:
        result = await self.db.execute(
            update(RideRequestModel)
            .where(RideRequestModel.id == request_id)
            .values(status="cancelled", updated_at=datetime.now(timezone.utc))
        )
        return result.rowcount > 0
