"""
Activity Service — FastAPI application.

ROUTES:
  POST /activities                  — Log an activity (internal use, no auth)
  GET  /users/{user_id}/activities  — List user activities (admin or self, cursor paginated)
  GET  /health                      — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import forbidden
from mobility_common.fastapi.middleware import get_current_user, TokenPayload
from mobility_common.fastapi.pagination import paginate, decode_cursor

import config as activity_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(activity_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Activity Service",
    version="0.1.0",
    description="Activity logging for Smart Mobility Platform — track user actions across services",
    lifespan=lifespan,
)


# -- Helper --

def _activity_response(activity) -> schemas.ActivityResponse:
    """Convert an ActivityModel to an ActivityResponse."""
    return schemas.ActivityResponse(
        id=activity.id,
        user_id=str(activity.user_id),
        action=activity.action,
        resource_type=activity.resource_type,
        resource_id=activity.resource_id,
        ip_address=str(activity.ip_address) if activity.ip_address else None,
        user_agent=activity.user_agent,
        metadata=activity.metadata_,
        created_at=activity.created_at,
    )


# -- Routes --


@app.post("/activities", response_model=schemas.ActivityResponse, status_code=201)
async def log_activity(
    body: schemas.LogActivityRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Log a new activity. Internal use — called by other services.

    No authentication required so that internal services can log
    activities without needing to forward user tokens.
    """
    repo = repository.ActivityRepository(db)
    activity = await repo.log_activity(
        user_id=body.user_id,
        action=body.action,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        ip_address=body.ip_address,
        user_agent=body.user_agent,
        metadata=body.metadata,
    )
    return _activity_response(activity)


@app.get("/users/{user_id}/activities", response_model=schemas.ActivityListResponse)
async def list_user_activities(
    user_id: str,
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List activities for a user. Admin can view anyone; users can only view their own."""
    if user.role != "admin" and user.sub != user_id:
        raise forbidden("You can only view your own activity log")

    repo = repository.ActivityRepository(db)

    decoded_cursor = int(decode_cursor(cursor)) if cursor else None
    activities = await repo.list_user_activities(
        user_id=user_id,
        cursor=decoded_cursor,
        limit=limit,
    )

    page = paginate(
        items=[_activity_response(a) for a in activities],
        limit=limit,
        cursor_field="id",
    )

    return schemas.ActivityListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=activity_config.settings.service_port,
        reload=activity_config.settings.debug,
    )
