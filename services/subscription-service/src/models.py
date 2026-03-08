"""
SQLAlchemy ORM models for the subscription service.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class SubscriptionModel(Base):
    """Maps to marketplace.subscriptions table."""
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "marketplace"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")
    price_per_month: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
