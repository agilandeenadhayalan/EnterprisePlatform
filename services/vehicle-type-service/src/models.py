"""SQLAlchemy ORM models for vehicle type service."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class VehicleTypeModel(Base):
    """Maps to vehicles.vehicle_types table."""
    __tablename__ = "vehicle_types"
    __table_args__ = {"schema": "vehicles"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="4")
    luggage_capacity: Mapped[int] = mapped_column(Integer, server_default="2")

    base_fare: Mapped[float] = mapped_column(Float, nullable=False, server_default="5.0")
    per_km_rate: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.5")
    per_minute_rate: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.25")
    minimum_fare: Mapped[float] = mapped_column(Float, nullable=False, server_default="8.0")
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    features: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
