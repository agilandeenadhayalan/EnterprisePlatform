"""SQLAlchemy ORM models for vehicle service."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class VehicleModel(Base):
    """Maps to vehicles.vehicles table."""
    __tablename__ = "vehicles"
    __table_args__ = {"schema": "vehicles"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    driver_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    vehicle_type_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))

    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    vin: Mapped[str | None] = mapped_column(String(17))
    status: Mapped[str] = mapped_column(String(30), server_default="active")
    capacity: Mapped[int] = mapped_column(Integer, server_default="4")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
