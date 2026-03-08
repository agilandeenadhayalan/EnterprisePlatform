"""
Notification Service — FastAPI application.

ROUTES:
  POST /notifications                      — Create a new notification
  GET  /users/{id}/notifications           — Get user's notifications
  PATCH /notifications/{id}/read           — Mark a notification as read
  POST /notifications/mark-all-read        — Mark all notifications as read
  GET  /users/{id}/notifications/unread-count — Get unread count
  GET  /health                             — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found

import config as service_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(service_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Notification Service",
    version="0.1.0",
    description="User notification management for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/notifications", response_model=schemas.NotificationResponse, status_code=201)
async def create_notification(
    body: schemas.CreateNotificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new notification for a user."""
    repo = repository.NotificationRepository(db)
    notification = await repo.create_notification(
        user_id=body.user_id,
        title=body.title,
        message=body.message,
        notification_type=body.notification_type,
        channel=body.channel,
    )
    return schemas.NotificationResponse(
        id=str(notification.id),
        user_id=str(notification.user_id),
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        channel=notification.channel,
        is_read=notification.is_read,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@app.get("/users/{user_id}/notifications", response_model=schemas.NotificationListResponse)
async def get_user_notifications(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all notifications for a user."""
    repo = repository.NotificationRepository(db)
    notifications = await repo.get_user_notifications(user_id)
    return schemas.NotificationListResponse(
        notifications=[
            schemas.NotificationResponse(
                id=str(n.id),
                user_id=str(n.user_id),
                title=n.title,
                message=n.message,
                notification_type=n.notification_type,
                channel=n.channel,
                is_read=n.is_read,
                read_at=n.read_at,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        count=len(notifications),
    )


@app.patch("/notifications/{notification_id}/read", response_model=schemas.NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    repo = repository.NotificationRepository(db)
    notification = await repo.mark_as_read(notification_id)
    if not notification:
        raise not_found("Notification", notification_id)
    return schemas.NotificationResponse(
        id=str(notification.id),
        user_id=str(notification.user_id),
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        channel=notification.channel,
        is_read=notification.is_read,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@app.post("/notifications/mark-all-read", response_model=schemas.MarkReadResponse)
async def mark_all_read(
    body: schemas.MarkAllReadRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications for a user as read."""
    repo = repository.NotificationRepository(db)
    count = await repo.mark_all_read(body.user_id)
    return schemas.MarkReadResponse(message="All notifications marked as read", count=count)


@app.get("/users/{user_id}/notifications/unread-count", response_model=schemas.UnreadCountResponse)
async def get_unread_count(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the count of unread notifications for a user."""
    repo = repository.NotificationRepository(db)
    count = await repo.get_unread_count(user_id)
    return schemas.UnreadCountResponse(user_id=user_id, unread_count=count)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
