"""
SQLAlchemy ORM models for the driver rating service.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class DriverRatingModel(Base):
    """Maps to drivers.driver_ratings table."""
    __tablename__ = "driver_ratings"
    __table_args__ = {"schema": "drivers"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    driver_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    rider_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
