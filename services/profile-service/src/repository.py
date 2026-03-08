"""
Profile service repository — database access layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import ProfileModel


class ProfileRepository:
    """Database operations for the profile service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user_id: str) -> Optional[ProfileModel]:
        """Get a user's profile by user_id."""
        result = await self.db.execute(
            select(ProfileModel).where(ProfileModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_profile(self, user_id: str, **fields) -> ProfileModel:
        """
        Create or fully replace a profile.

        If a profile exists for this user_id, update all fields.
        If not, create a new profile record.
        """
        existing = await self.get_profile(user_id)

        if existing:
            await self.db.execute(
                update(ProfileModel)
                .where(ProfileModel.user_id == user_id)
                .values(**fields, updated_at=datetime.utcnow())
            )
            return await self.get_profile(user_id)
        else:
            profile = ProfileModel(user_id=user_id, **fields)
            self.db.add(profile)
            await self.db.flush()
            return profile

    async def update_profile(self, user_id: str, **fields) -> Optional[ProfileModel]:
        """Update specific fields on an existing profile."""
        existing = await self.get_profile(user_id)
        if not existing:
            return None

        await self.db.execute(
            update(ProfileModel)
            .where(ProfileModel.user_id == user_id)
            .values(**fields, updated_at=datetime.utcnow())
        )
        return await self.get_profile(user_id)
