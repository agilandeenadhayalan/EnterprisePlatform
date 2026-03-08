"""
SQLAlchemy ORM models for the trip service.

Maps to the trips schema in PostgreSQL.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class TripModel(Base):
    """Maps to trips.trips table."""
    __tablename__ = "trips"
    __table_args__ = {"schema": "trips"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    rider_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    driver_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    vehicle_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))

    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="requested")

    pickup_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_address: Mapped[str | None] = mapped_column(String(500))

    dropoff_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_address: Mapped[str | None] = mapped_column(String(500))

    estimated_distance_km: Mapped[float | None] = mapped_column(Float)
    actual_distance_km: Mapped[float | None] = mapped_column(Float)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    actual_duration_minutes: Mapped[int | None] = mapped_column(Integer)

    fare_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")

    vehicle_type: Mapped[str | None] = mapped_column(String(50))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
