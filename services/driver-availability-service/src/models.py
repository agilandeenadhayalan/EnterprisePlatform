"""
SQLAlchemy ORM models for the driver availability service.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class DriverAvailabilityModel(Base):
    """Maps to drivers.driver_availability table."""
    __tablename__ = "driver_availability"
    __table_args__ = {"schema": "drivers"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    driver_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="offline")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    last_online_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_offline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_online_seconds: Mapped[int] = mapped_column(server_default="0")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
