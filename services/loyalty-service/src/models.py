"""
SQLAlchemy ORM models for the loyalty service.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class LoyaltyPointsModel(Base):
    """Maps to marketplace.loyalty_points table."""
    __tablename__ = "loyalty_points"
    __table_args__ = {"schema": "marketplace"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tier: Mapped[str] = mapped_column(String(50), nullable=False, server_default="bronze")
    lifetime_points: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class LoyaltyTransactionModel(Base):
    """Maps to marketplace.loyalty_transactions table."""
    __tablename__ = "loyalty_transactions"
    __table_args__ = {"schema": "marketplace"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reference_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
