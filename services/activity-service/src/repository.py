"""
Activity service repository — database access layer.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ActivityModel


class ActivityRepository:
    """Database operations for the activity service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_activity(
        self,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ActivityModel:
        """Insert a new activity log entry."""
        activity = ActivityModel(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata,
        )
        self.db.add(activity)
        await self.db.flush()
        return activity

    async def list_user_activities(
        self,
        user_id: str,
        cursor: Optional[int] = None,
        limit: int = 20,
    ) -> list[ActivityModel]:
        """
        List activities for a user with cursor-based pagination.

        Uses the BIGSERIAL id as cursor (descending order — newest first).
        Fetches limit+1 rows so the caller can detect if more pages exist.
        """
        query = (
            select(ActivityModel)
            .where(ActivityModel.user_id == user_id)
            .order_by(ActivityModel.id.desc())
        )

        if cursor:
            query = query.where(ActivityModel.id < cursor)

        query = query.limit(limit + 1)
        result = await self.db.execute(query)
        return list(result.scalars().all())
