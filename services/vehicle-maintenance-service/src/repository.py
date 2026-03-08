"""Vehicle maintenance repository — database access layer."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import VehicleMaintenanceModel


class VehicleMaintenanceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_maintenance(
        self,
        vehicle_id: str,
        maintenance_type: str,
        description: Optional[str] = None,
        cost: Optional[float] = None,
        service_provider: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        next_due_at: Optional[datetime] = None,
    ) -> VehicleMaintenanceModel:
        record = VehicleMaintenanceModel(
            vehicle_id=vehicle_id,
            maintenance_type=maintenance_type,
            description=description,
            cost=cost,
            service_provider=service_provider,
            scheduled_at=scheduled_at,
            next_due_at=next_due_at,
            status="scheduled",
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_vehicle_maintenance(self, vehicle_id: str) -> list[VehicleMaintenanceModel]:
        result = await self.db.execute(
            select(VehicleMaintenanceModel)
            .where(VehicleMaintenanceModel.vehicle_id == vehicle_id)
            .order_by(VehicleMaintenanceModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_upcoming_maintenance(self, limit: int = 20) -> list[VehicleMaintenanceModel]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(VehicleMaintenanceModel)
            .where(
                VehicleMaintenanceModel.status == "scheduled",
                VehicleMaintenanceModel.scheduled_at >= now,
            )
            .order_by(VehicleMaintenanceModel.scheduled_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
