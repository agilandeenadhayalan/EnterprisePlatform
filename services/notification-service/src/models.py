"""
SQLAlchemy ORM models for the notification service.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class NotificationModel(Base):
    """Maps to comms.notifications table."""
    __tablename__ = "notifications"
    __table_args__ = {"schema": "comms"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="info")
    channel: Mapped[str] = mapped_column(String(50), nullable=False, server_default="in_app")
    is_read: Mapped[bool] = mapped_column(Boolean, server_default="false")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
