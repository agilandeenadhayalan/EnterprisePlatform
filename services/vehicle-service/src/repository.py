"""Vehicle repository — database access layer."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import VehicleModel


class VehicleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_vehicle(
        self,
        make: str,
        model: str,
        year: int,
        color: str,
        license_plate: str,
        driver_id: Optional[str] = None,
        vehicle_type_id: Optional[str] = None,
        vin: Optional[str] = None,
        capacity: int = 4,
    ) -> VehicleModel:
        vehicle = VehicleModel(
            driver_id=driver_id,
            vehicle_type_id=vehicle_type_id,
            make=make,
            model=model,
            year=year,
            color=color,
            license_plate=license_plate,
            vin=vin,
            capacity=capacity,
        )
        self.db.add(vehicle)
        await self.db.flush()
        return vehicle

    async def get_vehicle_by_id(self, vehicle_id: str) -> Optional[VehicleModel]:
        result = await self.db.execute(
            select(VehicleModel).where(VehicleModel.id == vehicle_id)
        )
        return result.scalar_one_or_none()

    async def update_vehicle(self, vehicle_id: str, **fields) -> Optional[VehicleModel]:
        fields["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(VehicleModel)
            .where(VehicleModel.id == vehicle_id)
            .values(**fields)
        )
        return await self.get_vehicle_by_id(vehicle_id)

    async def delete_vehicle(self, vehicle_id: str) -> bool:
        result = await self.db.execute(
            delete(VehicleModel).where(VehicleModel.id == vehicle_id)
        )
        return result.rowcount > 0

    async def list_vehicles(self, limit: int = 50, offset: int = 0) -> list[VehicleModel]:
        result = await self.db.execute(
            select(VehicleModel)
            .order_by(VehicleModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_driver_vehicle(self, driver_id: str) -> Optional[VehicleModel]:
        result = await self.db.execute(
            select(VehicleModel)
            .where(VehicleModel.driver_id == driver_id, VehicleModel.is_active == True)
            .limit(1)
        )
        return result.scalar_one_or_none()
