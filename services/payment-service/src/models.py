"""SQLAlchemy ORM models for the payment service."""

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class PaymentModel(Base):
    """Maps to payments.payments table."""
    __tablename__ = "payments"
    __table_args__ = {"schema": "payments"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    rider_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    driver_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    payment_method_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    payment_gateway_ref: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
