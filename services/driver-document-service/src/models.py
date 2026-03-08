"""
SQLAlchemy ORM models for the driver document service.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class DriverDocumentModel(Base):
    """Maps to drivers.driver_documents table."""
    __tablename__ = "driver_documents"
    __table_args__ = {"schema": "drivers"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    driver_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(100))
    file_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    verified_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
