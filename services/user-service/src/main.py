"""
User Service — FastAPI application.

ROUTES:
  GET    /users         — List users with cursor pagination (admin only)
  GET    /users/me      — Get current user (requires auth)
  GET    /users/{user_id} — Get user by ID (admin or self)
  PATCH  /users/{user_id} — Update user fields (admin or self)
  DELETE /users/{user_id} — Deactivate user (admin only, soft delete)
  GET    /health        — Health check (provided by create_app)
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
from mobility_common.fastapi.errors import not_found, forbidden
from mobility_common.fastapi.middleware import get_current_user, require_role, TokenPayload
from mobility_common.fastapi.pagination import paginate, decode_cursor

import config as user_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(user_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="User Service",
    version="0.1.0",
    description="User management for Smart Mobility Platform — list, view, update, deactivate",
    lifespan=lifespan,
)


# -- Helper --

def _user_response(user) -> schemas.UserResponse:
    """Convert a UserModel to a UserResponse."""
    return schemas.UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


# -- Routes --


@app.get("/users/me", response_model=schemas.UserResponse)
async def get_current_user_profile(
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the currently authenticated user's data."""
    repo = repository.UserRepository(db)
    db_user = await repo.get_user_by_id(user.sub)
    if not db_user:
        raise not_found("User", user.sub)
    return _user_response(db_user)


@app.get("/users", response_model=schemas.UserListResponse)
async def list_users(
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all users with cursor-based pagination (admin only)."""
    repo = repository.UserRepository(db)

    decoded_cursor = decode_cursor(cursor) if cursor else None
    users = await repo.list_users(cursor=decoded_cursor, limit=limit)

    page = paginate(
        items=[_user_response(u) for u in users],
        limit=limit,
        cursor_field="id",
    )

    return schemas.UserListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@app.get("/users/{user_id}", response_model=schemas.UserResponse)
async def get_user(
    user_id: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user by ID. Admin can view anyone; regular users can only view themselves."""
    if user.role != "admin" and user.sub != user_id:
        raise forbidden("You can only view your own profile")

    repo = repository.UserRepository(db)
    db_user = await repo.get_user_by_id(user_id)
    if not db_user:
        raise not_found("User", user_id)
    return _user_response(db_user)


@app.patch("/users/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: str,
    body: schemas.UpdateUserRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user fields. Admin can update anyone; regular users can only update themselves."""
    if user.role != "admin" and user.sub != user_id:
        raise forbidden("You can only update your own profile")

    repo = repository.UserRepository(db)

    # Only include fields that were explicitly set
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        # Nothing to update — return current user
        db_user = await repo.get_user_by_id(user_id)
        if not db_user:
            raise not_found("User", user_id)
        return _user_response(db_user)

    db_user = await repo.update_user(user_id, **update_data)
    if not db_user:
        raise not_found("User", user_id)
    return _user_response(db_user)


@app.delete("/users/{user_id}", status_code=204)
async def deactivate_user(
    user_id: str,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user (admin only). Soft delete: sets is_active=False."""
    repo = repository.UserRepository(db)
    db_user = await repo.deactivate_user(user_id)
    if not db_user:
        raise not_found("User", user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=user_config.settings.service_port,
        reload=user_config.settings.debug,
    )
