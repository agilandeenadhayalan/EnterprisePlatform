"""
SQLAlchemy ORM models for the preferences service.

Maps to the users.preferences table — a key-value store for user settings
organized by category (e.g. notifications.email_enabled, ride.auto_tip_percent).
"""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class PreferenceModel(Base):
    """Maps to users.preferences table."""
    __tablename__ = "preferences"
    __table_args__ = {"schema": "users"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
