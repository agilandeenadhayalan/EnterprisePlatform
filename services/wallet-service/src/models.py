"""SQLAlchemy ORM models for the wallet service."""
from datetime import datetime
from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from mobility_common.fastapi.database import Base

class WalletModel(Base):
    __tablename__ = "wallets"
    __table_args__ = {"schema": "payments"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

class WalletTransactionModel(Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = {"schema": "payments"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    wallet_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # topup, debit, refund
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
