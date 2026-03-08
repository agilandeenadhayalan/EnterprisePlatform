"""
SQLAlchemy ORM models for the pricing service.

Tables:
  - pricing.pricing_rules: fare rates per vehicle type
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class PricingRuleModel(Base):
    """Maps to pricing.pricing_rules table."""
    __tablename__ = "pricing_rules"
    __table_args__ = {"schema": "pricing"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)
    base_fare: Mapped[float] = mapped_column(Float, nullable=False)
    per_mile_rate: Mapped[float] = mapped_column(Float, nullable=False)
    per_minute_rate: Mapped[float] = mapped_column(Float, nullable=False)
    booking_fee: Mapped[float] = mapped_column(Float, nullable=False, server_default="2.50")
    minimum_fare: Mapped[float] = mapped_column(Float, nullable=False, server_default="5.00")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
