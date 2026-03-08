"""SQLAlchemy ORM models for the discount service."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class DiscountModel(Base):
    """Maps to pricing.discounts table."""
    __tablename__ = "discounts"
    __table_args__ = {"schema": "pricing"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # percentage or fixed
    discount_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    current_uses: Mapped[int] = mapped_column(Integer, server_default="0")
    min_fare_amount: Mapped[float | None] = mapped_column(Float)
    max_discount_amount: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
