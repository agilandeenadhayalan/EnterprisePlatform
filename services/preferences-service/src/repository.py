"""
Preferences service repository — database access layer.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import PreferenceModel


class PreferenceRepository:
    """Database operations for the preferences service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_preferences(self, user_id: str) -> list[PreferenceModel]:
        """Get all preferences for a user, ordered by category and key."""
        result = await self.db.execute(
            select(PreferenceModel)
            .where(PreferenceModel.user_id == user_id)
            .order_by(PreferenceModel.category, PreferenceModel.key)
        )
        return list(result.scalars().all())

    async def get_preference(
        self,
        user_id: str,
        category: str,
        key: str,
    ) -> Optional[PreferenceModel]:
        """Get a specific preference by user_id, category, and key."""
        result = await self.db.execute(
            select(PreferenceModel).where(
                and_(
                    PreferenceModel.user_id == user_id,
                    PreferenceModel.category == category,
                    PreferenceModel.key == key,
                )
            )
        )
        return result.scalar_one_or_none()

    async def set_preference(
        self,
        user_id: str,
        category: str,
        key: str,
        value: Any,
    ) -> PreferenceModel:
        """
        Set a preference value (upsert).

        If the preference exists, update its value. Otherwise, create it.
        """
        existing = await self.get_preference(user_id, category, key)

        if existing:
            await self.db.execute(
                update(PreferenceModel)
                .where(PreferenceModel.id == existing.id)
                .values(value=value, updated_at=datetime.utcnow())
            )
            return await self.get_preference(user_id, category, key)
        else:
            pref = PreferenceModel(
                user_id=user_id,
                category=category,
                key=key,
                value=value,
            )
            self.db.add(pref)
            await self.db.flush()
            return pref

    async def delete_preference(
        self,
        user_id: str,
        category: str,
        key: str,
    ) -> bool:
        """Delete a specific preference. Returns True if a row was deleted."""
        result = await self.db.execute(
            delete(PreferenceModel).where(
                and_(
                    PreferenceModel.user_id == user_id,
                    PreferenceModel.category == category,
                    PreferenceModel.key == key,
                )
            )
        )
        return result.rowcount > 0
