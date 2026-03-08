"""SQLAlchemy ORM models for the promotion service."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class PromotionModel(Base):
    """Maps to pricing.promotions table."""
    __tablename__ = "promotions"
    __table_args__ = {"schema": "pricing"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    promotion_type: Mapped[str] = mapped_column(String(50), nullable=False)  # referral, seasonal, loyalty
    reward_type: Mapped[str] = mapped_column(String(20), nullable=False)  # percentage, fixed, free_ride
    reward_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_redemptions: Mapped[int | None] = mapped_column(Integer)
    current_redemptions: Mapped[int] = mapped_column(Integer, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
