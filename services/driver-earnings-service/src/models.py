"""
SQLAlchemy ORM models for the driver earnings service.
"""

from datetime import datetime, date

from sqlalchemy import Date, DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class DriverEarningModel(Base):
    """Maps to drivers.driver_earnings table."""
    __tablename__ = "driver_earnings"
    __table_args__ = {"schema": "drivers"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    driver_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    trip_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")
    earning_type: Mapped[str] = mapped_column(String(30), nullable=False, server_default="trip")
    description: Mapped[str | None] = mapped_column(String(255))
    earning_date: Mapped[date] = mapped_column(Date, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
