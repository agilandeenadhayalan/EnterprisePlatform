"""
Session service repository — database access layer.

Provides clean methods for querying and revoking sessions.
Auth-service creates sessions; session-service reads and deletes them.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import SessionModel


class SessionRepository:
    """Database operations for the session service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_sessions(self, user_id: str) -> list[SessionModel]:
        """Get all active (non-expired) sessions for a user."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(SessionModel)
            .where(
                SessionModel.user_id == user_id,
                SessionModel.expires_at > now,
            )
            .order_by(SessionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_session_by_id(self, session_id: str) -> Optional[SessionModel]:
        """Find a session by its UUID."""
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        return result.scalar_one_or_none()

    async def delete_session(self, session_id: str) -> bool:
        """
        Revoke a specific session by deleting it.

        Returns True if a session was actually deleted, False if not found.
        """
        result = await self.db.execute(
            delete(SessionModel).where(SessionModel.id == session_id)
        )
        return result.rowcount > 0

    async def count_active_sessions(self, user_id: str) -> int:
        """Count non-expired sessions for a user."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(func.count())
            .select_from(SessionModel)
            .where(
                SessionModel.user_id == user_id,
                SessionModel.expires_at > now,
            )
        )
        return result.scalar_one()
