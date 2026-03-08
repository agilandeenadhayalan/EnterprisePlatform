"""
SQLAlchemy ORM models for the feature flag service.

Maps to:
  - platform.feature_flags — global feature flag definitions
  - platform.flag_overrides — per-user overrides that bypass normal evaluation

The flag evaluation decision tree:
  1. Check user-specific override (if exists, it wins)
  2. Check if flag is globally enabled
  3. If enabled, check target_roles (user's role must match if set)
  4. Check rollout_percentage using hash(user_id + flag_name) % 100
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mobility_common.fastapi.database import Base


class FeatureFlagModel(Base):
    """Maps to platform.feature_flags table."""
    __tablename__ = "feature_flags"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    flag_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    target_roles: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    # Relationship to overrides
    overrides: Mapped[list["FlagOverrideModel"]] = relationship(
        back_populates="flag", cascade="all, delete-orphan"
    )


class FlagOverrideModel(Base):
    """Maps to platform.flag_overrides table."""
    __tablename__ = "flag_overrides"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    flag_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("platform.feature_flags.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    # Relationship back to flag
    flag: Mapped["FeatureFlagModel"] = relationship(back_populates="overrides")
