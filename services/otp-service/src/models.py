"""
SQLAlchemy ORM models for the OTP service.

Maps to the identity.otp_codes table created in init-postgres.sql.
OTP codes are hashed with SHA-256 before storing — the plaintext is
never persisted to the database.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class OtpCodeModel(Base):
    """Maps to identity.otp_codes table."""
    __tablename__ = "otp_codes"
    __table_args__ = {"schema": "identity"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, server_default="email")
    purpose: Mapped[str] = mapped_column(String(50), nullable=False, server_default="verification")
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, server_default="3")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
