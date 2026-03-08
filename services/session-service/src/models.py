"""
SQLAlchemy ORM models for the session service.

Maps to the identity.user_sessions table created in init-postgres.sql.
The session-service reads and deletes session records; auth-service creates them.
"""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


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
