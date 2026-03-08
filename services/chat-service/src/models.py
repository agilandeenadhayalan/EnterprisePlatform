"""
SQLAlchemy ORM models for the chat service.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class ChatRoomModel(Base):
    """Maps to comms.chat_rooms table."""
    __tablename__ = "chat_rooms"
    __table_args__ = {"schema": "comms"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    trip_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), index=True)
    room_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="trip")
    participant_ids: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class ChatMessageModel(Base):
    """Maps to comms.chat_messages table."""
    __tablename__ = "chat_messages"
    __table_args__ = {"schema": "comms"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    room_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    sender_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="text")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
