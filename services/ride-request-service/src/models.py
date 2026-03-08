"""
SQLAlchemy ORM models for the ride request service.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class RideRequestModel(Base):
    """Maps to trips.ride_requests table."""
    __tablename__ = "ride_requests"
    __table_args__ = {"schema": "trips"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    rider_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")

    pickup_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_address: Mapped[str | None] = mapped_column(String(500))

    dropoff_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_address: Mapped[str | None] = mapped_column(String(500))

    vehicle_type: Mapped[str | None] = mapped_column(String(50))
    estimated_fare: Mapped[float | None] = mapped_column(Float)

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
