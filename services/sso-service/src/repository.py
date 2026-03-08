"""
SSO service repository — database access layer.

Handles all SQL operations for SSO providers and user-provider connections.
The actual OAuth token exchange is mocked in this service — a real
implementation would call the provider's token endpoint.
"""

import secrets
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import SsoProviderModel, SsoConnectionModel


class SsoRepository:
    """Database operations for the SSO service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- Provider operations --

    async def list_enabled_providers(self) -> list[SsoProviderModel]:
        """Return all enabled SSO providers."""
        result = await self.db.execute(
            select(SsoProviderModel)
            .where(SsoProviderModel.is_enabled == True)
            .order_by(SsoProviderModel.name)
        )
        return list(result.scalars().all())

    async def get_provider_by_name(self, name: str) -> Optional[SsoProviderModel]:
        """Find an SSO provider by name."""
        result = await self.db.execute(
            select(SsoProviderModel).where(SsoProviderModel.name == name)
        )
        return result.scalar_one_or_none()

    async def get_provider_by_id(self, provider_id: str) -> Optional[SsoProviderModel]:
        """Find an SSO provider by UUID."""
        result = await self.db.execute(
            select(SsoProviderModel).where(SsoProviderModel.id == provider_id)
        )
        return result.scalar_one_or_none()

    # -- Authorization URL generation --

    def build_authorization_url(
        self, provider: SsoProviderModel, redirect_uri: str, state: str
    ) -> str:
        """
        Build the authorization URL for a provider.

        In production, this would construct a proper OAuth2 authorization URL
        with the provider's client_id and scopes. Here we build it from the
        provider's stored configuration.
        """
        if not provider.authorization_url:
            # Fallback for providers without a configured auth URL
            return f"https://{provider.name}.example.com/oauth/authorize"

        params = {
            "client_id": provider.client_id or "mock-client-id",
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": provider.scopes or "openid email profile",
            "state": state,
        }
        return f"{provider.authorization_url}?{urlencode(params)}"

    @staticmethod
    def generate_state() -> str:
        """Generate a cryptographically random state parameter for CSRF protection."""
        return secrets.token_urlsafe(32)

    # -- Connection operations --

    async def get_user_connections(
        self, user_id: str
    ) -> list[tuple[SsoConnectionModel, SsoProviderModel]]:
        """Get all SSO connections for a user (with provider details)."""
        result = await self.db.execute(
            select(SsoConnectionModel, SsoProviderModel)
            .join(SsoProviderModel, SsoConnectionModel.provider_id == SsoProviderModel.id)
            .where(SsoConnectionModel.user_id == user_id)
        )
        return list(result.all())

    async def get_connection_by_id(self, connection_id: str) -> Optional[SsoConnectionModel]:
        """Find a connection by UUID."""
        result = await self.db.execute(
            select(SsoConnectionModel).where(SsoConnectionModel.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def get_connection_by_external(
        self, provider_id: str, external_user_id: str
    ) -> Optional[SsoConnectionModel]:
        """Find a connection by provider + external user ID."""
        result = await self.db.execute(
            select(SsoConnectionModel).where(
                SsoConnectionModel.provider_id == provider_id,
                SsoConnectionModel.external_user_id == external_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_connection(
        self,
        user_id: str,
        provider_id: str,
        external_user_id: str,
        external_email: Optional[str] = None,
        external_name: Optional[str] = None,
    ) -> SsoConnectionModel:
        """Create a new SSO connection linking a user to an external identity."""
        connection = SsoConnectionModel(
            user_id=user_id,
            provider_id=provider_id,
            external_user_id=external_user_id,
            external_email=external_email,
            external_name=external_name,
            last_login_at=datetime.utcnow(),
        )
        self.db.add(connection)
        await self.db.flush()
        return connection

    async def delete_connection(self, connection_id: str) -> bool:
        """Remove an SSO connection. Returns True if a row was deleted."""
        result = await self.db.execute(
            delete(SsoConnectionModel).where(SsoConnectionModel.id == connection_id)
        )
        return result.rowcount > 0
