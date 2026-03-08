"""
Profile Service — FastAPI application.

ROUTES:
  GET  /profiles/{user_id}  — Get user profile
  PUT  /profiles/{user_id}  — Create or update profile (owner or admin)
  PATCH /profiles/{user_id} — Partial update (owner or admin)
  GET  /health              — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, forbidden
from mobility_common.fastapi.middleware import get_current_user, TokenPayload

import config as profile_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(profile_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Profile Service",
    version="0.1.0",
    description="User profile management for Smart Mobility Platform — avatar, bio, preferences",
    lifespan=lifespan,
)


# -- Helper --

def _profile_response(profile) -> schemas.ProfileResponse:
    """Convert a ProfileModel to a ProfileResponse."""
    return schemas.ProfileResponse(
        user_id=str(profile.user_id),
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        date_of_birth=profile.date_of_birth,
        language=profile.language,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# -- Routes --


@app.get("/profiles/{user_id}", response_model=schemas.ProfileResponse)
async def get_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a user's profile by user_id."""
    repo = repository.ProfileRepository(db)
    profile = await repo.get_profile(user_id)
    if not profile:
        raise not_found("Profile", user_id)
    return _profile_response(profile)


@app.put("/profiles/{user_id}", response_model=schemas.ProfileResponse)
async def create_or_update_profile(
    user_id: str,
    body: schemas.CreateProfileRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or fully replace a user's profile. Owner or admin only."""
    if user.role != "admin" and user.sub != user_id:
        raise forbidden("You can only manage your own profile")

    repo = repository.ProfileRepository(db)
    profile_data = body.model_dump(exclude_unset=True)
    profile = await repo.upsert_profile(user_id, **profile_data)
    return _profile_response(profile)


@app.patch("/profiles/{user_id}", response_model=schemas.ProfileResponse)
async def partial_update_profile(
    user_id: str,
    body: schemas.UpdateProfileRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partial update of a user's profile. Owner or admin only."""
    if user.role != "admin" and user.sub != user_id:
        raise forbidden("You can only manage your own profile")

    repo = repository.ProfileRepository(db)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        profile = await repo.get_profile(user_id)
        if not profile:
            raise not_found("Profile", user_id)
        return _profile_response(profile)

    profile = await repo.update_profile(user_id, **update_data)
    if not profile:
        raise not_found("Profile", user_id)
    return _profile_response(profile)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=profile_config.settings.service_port,
        reload=profile_config.settings.debug,
    )
