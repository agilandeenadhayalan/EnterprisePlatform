"""
SQLAlchemy ORM models for the support ticket service.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class SupportTicketModel(Base):
    """Maps to marketplace.support_tickets table."""
    __tablename__ = "support_tickets"
    __table_args__ = {"schema": "marketplace"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, server_default="general")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, server_default="medium")
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="open")
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
