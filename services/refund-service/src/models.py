"""SQLAlchemy ORM models for the refund service."""
from datetime import datetime
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from mobility_common.fastapi.database import Base

class RefundModel(Base):
    __tablename__ = "refunds"
    __table_args__ = {"schema": "payments"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    payment_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    rider_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
