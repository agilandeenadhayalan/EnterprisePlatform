"""
SQLAlchemy ORM models for the driver service.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class DriverModel(Base):
    """Maps to drivers.drivers table."""
    __tablename__ = "drivers"
    __table_args__ = {"schema": "drivers"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    license_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(30), nullable=False, server_default="sedan")
    vehicle_make: Mapped[str | None] = mapped_column(String(50))
    vehicle_model: Mapped[str | None] = mapped_column(String(50))
    vehicle_year: Mapped[int | None] = mapped_column(Integer)
    vehicle_plate: Mapped[str | None] = mapped_column(String(20))
    rating: Mapped[float] = mapped_column(Float, server_default="5.0")
    total_trips: Mapped[int] = mapped_column(Integer, server_default="0")
    acceptance_rate: Mapped[float] = mapped_column(Float, server_default="1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, server_default="false")
    status: Mapped[str] = mapped_column(String(20), server_default="offline")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
