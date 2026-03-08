"""SQLAlchemy ORM models for vehicle maintenance service."""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class VehicleMaintenanceModel(Base):
    """Maps to vehicles.vehicle_maintenance table."""
    __tablename__ = "vehicle_maintenance"
    __table_args__ = {"schema": "vehicles"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    vehicle_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)

    maintenance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), server_default="scheduled")
    description: Mapped[str | None] = mapped_column(Text)

    cost: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")

    service_provider: Mapped[str | None] = mapped_column(String(255))
    parts_replaced: Mapped[dict | None] = mapped_column(JSONB)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
