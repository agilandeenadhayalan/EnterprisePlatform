"""
Config service repository — database access layer.

Provides clean methods for CRUD operations on the platform.configurations table.
Key design: every update increments the version number, so downstream services
can detect config changes by comparing their cached version against the DB.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import ConfigurationModel


class ConfigRepository:
    """Database operations for the config service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self, service_filter: Optional[str] = None) -> list[ConfigurationModel]:
        """
        Return all configuration entries, optionally filtered by service name.

        Used by the admin GET /configs endpoint. Ordered by service then key
        for predictable output.
        """
        query = select(ConfigurationModel).order_by(
            ConfigurationModel.service, ConfigurationModel.key
        )
        if service_filter:
            query = query.where(ConfigurationModel.service == service_filter)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_service(self, service: str) -> list[ConfigurationModel]:
        """Get all configs for a specific service."""
        result = await self.db.execute(
            select(ConfigurationModel)
            .where(ConfigurationModel.service == service)
            .order_by(ConfigurationModel.key)
        )
        return list(result.scalars().all())

    async def get_by_service_key(self, service: str, key: str) -> Optional[ConfigurationModel]:
        """Find a specific config entry by service + key."""
        result = await self.db.execute(
            select(ConfigurationModel).where(
                ConfigurationModel.service == service,
                ConfigurationModel.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def set_config(
        self,
        service: str,
        key: str,
        value: any,
        description: Optional[str],
        updated_by: str,
    ) -> ConfigurationModel:
        """
        Create or update a config entry.

        If the entry already exists, increments the version and updates the
        value, description, and timestamps. If it doesn't exist, creates it
        with version=1.
        """
        existing = await self.get_by_service_key(service, key)
        now = datetime.now(timezone.utc)

        if existing:
            # Update: increment version
            existing.value = value
            existing.version = existing.version + 1
            existing.updated_by = updated_by
            existing.updated_at = now
            if description is not None:
                existing.description = description
            await self.db.flush()
            return existing
        else:
            # Create new entry
            entry = ConfigurationModel(
                service=service,
                key=key,
                value=value,
                description=description,
                version=1,
                updated_by=updated_by,
                created_at=now,
                updated_at=now,
            )
            self.db.add(entry)
            await self.db.flush()
            return entry

    async def delete_config(self, service: str, key: str) -> bool:
        """
        Delete a config entry by service + key.

        Returns True if a row was actually deleted, False if not found.
        """
        result = await self.db.execute(
            delete(ConfigurationModel).where(
                ConfigurationModel.service == service,
                ConfigurationModel.key == key,
            )
        )
        return result.rowcount > 0
