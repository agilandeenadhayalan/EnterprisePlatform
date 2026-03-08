"""SQLAlchemy ORM models for ride feedback."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class RideFeedbackModel(Base):
    """Maps to trips.ride_feedback table."""
    __tablename__ = "ride_feedback"
    __table_args__ = {"schema": "trips"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    rider_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    driver_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)

    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text)
    feedback_type: Mapped[str] = mapped_column(String(20), server_default="rider_to_driver")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
