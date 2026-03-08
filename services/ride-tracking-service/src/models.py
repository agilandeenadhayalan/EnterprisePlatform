"""SQLAlchemy ORM models for ride tracking."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class RideTrackingModel(Base):
    """Maps to trips.ride_tracking table."""
    __tablename__ = "ride_tracking"
    __table_args__ = {"schema": "trips"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude: Mapped[float | None] = mapped_column(Float)
    speed_kmh: Mapped[float | None] = mapped_column(Float)
    heading: Mapped[float | None] = mapped_column(Float)
    accuracy_meters: Mapped[float | None] = mapped_column(Float)

    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
