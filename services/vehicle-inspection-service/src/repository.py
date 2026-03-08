"""Vehicle inspection repository — database access layer."""

from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import VehicleInspectionModel


VALID_STATUSES = ["scheduled", "in_progress", "passed", "failed", "cancelled"]


class VehicleInspectionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_inspection(
        self,
        vehicle_id: str,
        inspection_type: str,
        inspector_id: Optional[str] = None,
        notes: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> VehicleInspectionModel:
        inspection = VehicleInspectionModel(
            vehicle_id=vehicle_id,
            inspector_id=inspector_id,
            inspection_type=inspection_type,
            notes=notes,
            scheduled_at=scheduled_at,
            status="scheduled",
        )
        self.db.add(inspection)
        await self.db.flush()
        return inspection

    async def get_inspection_by_id(self, inspection_id: str) -> Optional[VehicleInspectionModel]:
        result = await self.db.execute(
            select(VehicleInspectionModel).where(VehicleInspectionModel.id == inspection_id)
        )
        return result.scalar_one_or_none()

    async def get_vehicle_inspections(self, vehicle_id: str) -> list[VehicleInspectionModel]:
        result = await self.db.execute(
            select(VehicleInspectionModel)
            .where(VehicleInspectionModel.vehicle_id == vehicle_id)
            .order_by(VehicleInspectionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_inspection_status(
        self,
        inspection_id: str,
        status: str,
        notes: Optional[str] = None,
        findings: Optional[dict[str, Any]] = None,
    ) -> Optional[VehicleInspectionModel]:
        values: dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if notes is not None:
            values["notes"] = notes
        if findings is not None:
            values["findings"] = findings
        if status in ("passed", "failed"):
            values["completed_at"] = datetime.now(timezone.utc)

        await self.db.execute(
            update(VehicleInspectionModel)
            .where(VehicleInspectionModel.id == inspection_id)
            .values(**values)
        )
        return await self.get_inspection_by_id(inspection_id)
