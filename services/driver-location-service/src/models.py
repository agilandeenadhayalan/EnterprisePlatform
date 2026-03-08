"""
SQLAlchemy ORM models for the driver location service.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class DriverLocationModel(Base):
    """Maps to drivers.driver_locations table."""
    __tablename__ = "driver_locations"
    __table_args__ = {"schema": "drivers"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    driver_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    heading: Mapped[float | None] = mapped_column(Float)
    speed: Mapped[float | None] = mapped_column(Float)
    accuracy: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20), server_default="gps")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
