"""
Preferences Service — FastAPI application.

ROUTES:
  GET    /preferences/{user_id}                    — Get all preferences (owner or admin)
  GET    /preferences/{user_id}/{category}/{key}   — Get specific preference
  PUT    /preferences/{user_id}/{category}/{key}   — Set preference value
  DELETE /preferences/{user_id}/{category}/{key}   — Reset preference to default
  GET    /health                                   — Health check (provided by create_app)
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

import config as pref_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(pref_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Preferences Service",
    version="0.1.0",
    description="User preferences for Smart Mobility Platform — key-value settings by category",
    lifespan=lifespan,
)


# -- Helper --

def _preference_response(pref) -> schemas.PreferenceResponse:
    """Convert a PreferenceModel to a PreferenceResponse."""
    return schemas.PreferenceResponse(
        category=pref.category,
        key=pref.key,
        value=pref.value,
        updated_at=pref.updated_at,
    )


def _check_access(user: "TokenPayload", user_id: str) -> None:
    """Ensure the requester is the owner or an admin."""
    if user.role != "admin" and user.sub != user_id:
        raise forbidden("You can only manage your own preferences")


# -- Routes --


@app.get("/preferences/{user_id}", response_model=schemas.PreferenceListResponse)
async def get_all_preferences(
    user_id: str,
    user: "TokenPayload" = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all preferences for a user. Owner or admin only."""
    _check_access(user, user_id)

    repo = repository.PreferenceRepository(db)
    prefs = await repo.get_all_preferences(user_id)

    return schemas.PreferenceListResponse(
        user_id=user_id,
        preferences=[_preference_response(p) for p in prefs],
    )


@app.get(
    "/preferences/{user_id}/{category}/{key}",
    response_model=schemas.PreferenceResponse,
)
async def get_preference(
    user_id: str,
    category: str,
    key: str,
    user: "TokenPayload" = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific preference by category and key."""
    _check_access(user, user_id)

    repo = repository.PreferenceRepository(db)
    pref = await repo.get_preference(user_id, category, key)
    if not pref:
        raise not_found("Preference", f"{category}/{key}")
    return _preference_response(pref)


@app.put(
    "/preferences/{user_id}/{category}/{key}",
    response_model=schemas.PreferenceResponse,
)
async def set_preference(
    user_id: str,
    category: str,
    key: str,
    body: schemas.SetPreferenceRequest,
    user: "TokenPayload" = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a preference value (creates or updates)."""
    _check_access(user, user_id)

    repo = repository.PreferenceRepository(db)
    pref = await repo.set_preference(user_id, category, key, body.value)
    return _preference_response(pref)


@app.delete("/preferences/{user_id}/{category}/{key}", status_code=204)
async def delete_preference(
    user_id: str,
    category: str,
    key: str,
    user: "TokenPayload" = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset a preference to default by deleting the stored value."""
    _check_access(user, user_id)

    repo = repository.PreferenceRepository(db)
    deleted = await repo.delete_preference(user_id, category, key)
    if not deleted:
        raise not_found("Preference", f"{category}/{key}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=pref_config.settings.service_port,
        reload=pref_config.settings.debug,
    )
