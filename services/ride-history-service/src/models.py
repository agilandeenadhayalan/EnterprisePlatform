"""
SQLAlchemy ORM models for ride history — read-only view of trips.trips table.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class TripModel(Base):
    """Read-only view of trips.trips table for history queries."""
    __tablename__ = "trips"
    __table_args__ = {"schema": "trips"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    rider_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    driver_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    pickup_address: Mapped[str | None] = mapped_column(String(500))
    dropoff_address: Mapped[str | None] = mapped_column(String(500))
    pickup_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    actual_distance_km: Mapped[float | None] = mapped_column(Float)
    actual_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    fare_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")
    vehicle_type: Mapped[str | None] = mapped_column(String(50))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
