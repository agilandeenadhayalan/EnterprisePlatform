"""SQLAlchemy ORM models for the payout service."""
from datetime import datetime
from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from mobility_common.fastapi.database import Base

class PayoutModel(Base):
    __tablename__ = "payouts"
    __table_args__ = {"schema": "payments"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    driver_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    payout_method: Mapped[str | None] = mapped_column(String(50))
    reference: Mapped[str | None] = mapped_column(String(255))
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
