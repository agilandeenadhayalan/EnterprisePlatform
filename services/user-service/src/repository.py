"""
User service repository — database access layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserModel


class UserRepository:
    """Database operations for the user service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        """Find a user by UUID."""
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> list[UserModel]:
        """
        List users with cursor-based pagination.

        Fetches limit+1 rows so the caller can detect if more pages exist.
        """
        query = select(UserModel).order_by(UserModel.created_at.desc(), UserModel.id)

        if cursor:
            query = query.where(UserModel.id > cursor)

        query = query.limit(limit + 1)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_user(self, user_id: str, **fields) -> Optional[UserModel]:
        """Update specific fields on a user record."""
        await self.db.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(**fields, updated_at=datetime.utcnow())
        )
        return await self.get_user_by_id(user_id)

    async def deactivate_user(self, user_id: str) -> Optional[UserModel]:
        """Soft-delete a user by setting is_active=False."""
        return await self.update_user(user_id, is_active=False)
