"""Vehicle type repository — database access layer."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import VehicleTypeModel


class VehicleTypeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_vehicle_types(self, active_only: bool = True) -> list[VehicleTypeModel]:
        query = select(VehicleTypeModel)
        if active_only:
            query = query.where(VehicleTypeModel.is_active == True)
        query = query.order_by(VehicleTypeModel.base_fare.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_vehicle_type_by_id(self, type_id: str) -> Optional[VehicleTypeModel]:
        result = await self.db.execute(
            select(VehicleTypeModel).where(VehicleTypeModel.id == type_id)
        )
        return result.scalar_one_or_none()
