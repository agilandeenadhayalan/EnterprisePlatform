"""
SQLAlchemy ORM models for the auth service.

WHY ORM models separate from Pydantic schemas?
- ORM models map to database tables (SQLAlchemy handles SQL generation)
- Pydantic schemas define API request/response shapes
- They often have different fields: the DB model has password_hash,
  but the API response schema never includes it

This separation follows the "ports and adapters" pattern — the database
is an implementation detail behind the repository layer.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class UserModel(Base):
    """Maps to identity.users table."""
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="rider")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class SessionModel(Base):
    """Maps to identity.user_sessions table."""
    __tablename__ = "user_sessions"
    __table_args__ = {"schema": "identity"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(512), nullable=False)
    device_info: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
