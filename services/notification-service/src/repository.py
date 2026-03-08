"""
Notification service repository — database access layer.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import NotificationModel


class NotificationRepository:
    """Database operations for the notification service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        channel: str = "in_app",
    ) -> NotificationModel:
        """Insert a new notification record."""
        notification = NotificationModel(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            channel=channel,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def get_user_notifications(self, user_id: str, limit: int = 50) -> List[NotificationModel]:
        """Get notifications for a user, ordered by most recent."""
        result = await self.db.execute(
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: str) -> Optional[NotificationModel]:
        """Mark a single notification as read."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(NotificationModel)
            .where(NotificationModel.id == notification_id)
            .values(is_read=True, read_at=now)
        )
        result = await self.db.execute(
            select(NotificationModel).where(NotificationModel.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def mark_all_read(self, user_id: str) -> int:
        """Mark all unread notifications for a user as read."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read.is_(False),
            )
            .values(is_read=True, read_at=now)
        )
        return result.rowcount

    async def get_unread_count(self, user_id: str) -> int:
        """Count unread notifications for a user."""
        result = await self.db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read.is_(False),
            )
        )
        return result.scalar_one()
