"""
SQLAlchemy ORM models for the SSO service.

Maps to identity.sso_providers and identity.sso_connections tables.
Providers are configured SSO integrations (Google, GitHub, etc.).
Connections link a user account to an external identity.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from mobility_common.fastapi.database import Base


class SsoProviderModel(Base):
    """Maps to identity.sso_providers table."""
    __tablename__ = "sso_providers"
    __table_args__ = {"schema": "identity"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    client_id: Mapped[str | None] = mapped_column(String(255))
    client_secret: Mapped[str | None] = mapped_column(String(512))
    authorization_url: Mapped[str | None] = mapped_column(Text)
    token_url: Mapped[str | None] = mapped_column(Text)
    userinfo_url: Mapped[str | None] = mapped_column(Text)
    scopes: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    config: Mapped[dict | None] = mapped_column(JSONB, server_default="'{}'::jsonb")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class SsoConnectionModel(Base):
    """Maps to identity.sso_connections table — links users to SSO identities."""
    __tablename__ = "sso_connections"
    __table_args__ = {"schema": "identity"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_email: Mapped[str | None] = mapped_column(String(255))
    external_name: Mapped[str | None] = mapped_column(String(255))
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
