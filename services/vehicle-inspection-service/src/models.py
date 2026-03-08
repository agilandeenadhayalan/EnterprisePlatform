"""SQLAlchemy ORM models for vehicle inspection service."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class VehicleInspectionModel(Base):
    """Maps to vehicles.vehicle_inspections table."""
    __tablename__ = "vehicle_inspections"
    __table_args__ = {"schema": "vehicles"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    vehicle_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    inspector_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))

    inspection_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), server_default="scheduled")

    notes: Mapped[str | None] = mapped_column(Text)
    findings: Mapped[dict | None] = mapped_column(JSONB)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
