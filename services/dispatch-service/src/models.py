"""
SQLAlchemy ORM models for the dispatch service.

Tables:
  - dispatch.dispatch_assignments: tracks driver-to-trip assignments
  - dispatch.dispatch_zones: defines geographic zones for dispatch logic
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class DispatchAssignmentModel(Base):
    """Maps to dispatch.dispatch_assignments table."""
    __tablename__ = "dispatch_assignments"
    __table_args__ = {"schema": "dispatch"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    driver_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    distance_to_pickup: Mapped[float | None] = mapped_column(Float)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class DispatchZoneModel(Base):
    """Maps to dispatch.dispatch_zones table."""
    __tablename__ = "dispatch_zones"
    __table_args__ = {"schema": "dispatch"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    lat_min: Mapped[float] = mapped_column(Float, nullable=False)
    lat_max: Mapped[float] = mapped_column(Float, nullable=False)
    lon_min: Mapped[float] = mapped_column(Float, nullable=False)
    lon_max: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
