"""
SQLAlchemy ORM models for the surge service.

Tables:
  - pricing.surge_zones: active surge multipliers by zone
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class SurgeZoneModel(Base):
    """Maps to pricing.surge_zones table."""
    __tablename__ = "surge_zones"
    __table_args__ = {"schema": "pricing"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    zone_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    zone_name: Mapped[str] = mapped_column(String(200), nullable=False)
    surge_multiplier: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    demand_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    supply_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    last_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
