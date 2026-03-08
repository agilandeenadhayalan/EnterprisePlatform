"""
SQLAlchemy ORM models for the profile service.

Maps to the users.profiles table — extended user profile data like
avatar, bio, date of birth, language, and timezone preferences.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class ProfileModel(Base):
    """Maps to users.profiles table."""
    __tablename__ = "profiles"
    __table_args__ = {"schema": "users"}

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    bio: Mapped[str | None] = mapped_column(Text)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    language: Mapped[str | None] = mapped_column(String(10), server_default="en")
    timezone: Mapped[str | None] = mapped_column(String(50), server_default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
