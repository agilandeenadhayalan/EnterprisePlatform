"""
SQLAlchemy ORM models for the access-control service.

Maps to the identity.roles and identity.user_roles tables. Roles contain a
JSONB permissions column that stores an array of permission strings. Wildcard
matching (e.g., "user:*") allows flexible permission hierarchies.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class RoleModel(Base):
    """Maps to identity.roles table."""
    __tablename__ = "roles"
    __table_args__ = {"schema": "identity"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[dict | None] = mapped_column(JSONB, server_default="'[]'::jsonb")
    is_system: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class UserRoleModel(Base):
    """Maps to identity.user_roles table — join table between users and roles."""
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "identity"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    role_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    assigned_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
