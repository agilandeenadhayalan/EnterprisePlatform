"""SQLAlchemy ORM models for the payment method service."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from mobility_common.fastapi.database import Base

class PaymentMethodModel(Base):
    """Maps to payments.payment_methods table."""
    __tablename__ = "payment_methods"
    __table_args__ = {"schema": "payments"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    method_type: Mapped[str] = mapped_column(String(30), nullable=False)  # card, bank_account, wallet
    provider: Mapped[str | None] = mapped_column(String(50))  # visa, mastercard, etc.
    last_four: Mapped[str | None] = mapped_column(String(4))
    expiry_month: Mapped[str | None] = mapped_column(String(2))
    expiry_year: Mapped[str | None] = mapped_column(String(4))
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    token_ref: Mapped[str | None] = mapped_column(String(255))  # payment gateway token
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
