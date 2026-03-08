"""
Feature Flag Service — FastAPI application.

ROUTES:
  GET    /flags                                — List all feature flags (admin only)
  GET    /flags/{flag_name}                    — Get flag details
  POST   /flags                                — Create a new flag (admin only)
  PUT    /flags/{flag_name}                    — Update flag (admin only)
  DELETE /flags/{flag_name}                    — Delete flag (admin only)
  GET    /flags/evaluate/{flag_name}           — Evaluate flag for current user
  POST   /flags/{flag_name}/overrides          — Set user-specific override (admin only)
  DELETE /flags/{flag_name}/overrides/{user_id} — Remove override (admin only)
  GET    /health                               — Health check (provided by create_app)

The evaluate endpoint implements a decision tree:
  1. User override > 2. Global toggle > 3. Role targeting > 4. Rollout %
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
from mobility_common.fastapi.errors import not_found, conflict
from mobility_common.fastapi.middleware import get_current_user, require_role, TokenPayload

import config as ff_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(ff_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Feature Flag Service",
    version="0.1.0",
    description="Feature toggles with rollout percentages, role targeting, and user overrides",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/flags/evaluate/{flag_name}", response_model=schemas.EvaluateFlagResponse)
async def evaluate_flag(
    flag_name: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluate whether a flag is enabled for the current user.

    Decision tree:
      1. Check user-specific override
      2. Check if flag is globally enabled
      3. Check target_roles (if specified, user's role must match)
      4. Check rollout_percentage using deterministic hash
    """
    repo = repository.FeatureFlagRepository(db)
    is_enabled, reason = await repo.evaluate_flag(flag_name, user.sub, user.role)

    return schemas.EvaluateFlagResponse(
        flag_name=flag_name,
        is_enabled=is_enabled,
        reason=reason,
    )


@app.get("/flags", response_model=schemas.FlagListResponse)
async def list_flags(
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all feature flags. Admin only."""
    repo = repository.FeatureFlagRepository(db)
    flags = await repo.list_flags()

    flag_list = [
        schemas.FlagResponse(
            id=str(f.id),
            flag_name=f.flag_name,
            description=f.description,
            is_enabled=f.is_enabled,
            rollout_percentage=f.rollout_percentage,
            target_roles=f.target_roles,
            metadata=f.metadata_,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
        for f in flags
    ]
    return schemas.FlagListResponse(flags=flag_list, count=len(flag_list))


@app.get("/flags/{flag_name}", response_model=schemas.FlagResponse)
async def get_flag(
    flag_name: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific feature flag."""
    repo = repository.FeatureFlagRepository(db)
    flag = await repo.get_by_name(flag_name)

    if not flag:
        raise not_found("FeatureFlag", flag_name)

    return schemas.FlagResponse(
        id=str(flag.id),
        flag_name=flag.flag_name,
        description=flag.description,
        is_enabled=flag.is_enabled,
        rollout_percentage=flag.rollout_percentage,
        target_roles=flag.target_roles,
        metadata=flag.metadata_,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


@app.post("/flags", response_model=schemas.FlagResponse, status_code=201)
async def create_flag(
    body: schemas.CreateFlagRequest,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new feature flag. Admin only."""
    repo = repository.FeatureFlagRepository(db)

    # Check for duplicate flag name
    existing = await repo.get_by_name(body.flag_name)
    if existing:
        raise conflict(f"Feature flag '{body.flag_name}' already exists")

    flag = await repo.create_flag(
        flag_name=body.flag_name,
        description=body.description,
        is_enabled=body.is_enabled,
        rollout_percentage=body.rollout_percentage,
        target_roles=body.target_roles,
        metadata=body.metadata,
    )

    return schemas.FlagResponse(
        id=str(flag.id),
        flag_name=flag.flag_name,
        description=flag.description,
        is_enabled=flag.is_enabled,
        rollout_percentage=flag.rollout_percentage,
        target_roles=flag.target_roles,
        metadata=flag.metadata_,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


@app.put("/flags/{flag_name}", response_model=schemas.FlagResponse)
async def update_flag(
    flag_name: str,
    body: schemas.UpdateFlagRequest,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing feature flag. Admin only."""
    repo = repository.FeatureFlagRepository(db)
    flag = await repo.get_by_name(flag_name)

    if not flag:
        raise not_found("FeatureFlag", flag_name)

    flag = await repo.update_flag(
        flag,
        description=body.description,
        is_enabled=body.is_enabled,
        rollout_percentage=body.rollout_percentage,
        target_roles=body.target_roles,
        metadata=body.metadata,
    )

    return schemas.FlagResponse(
        id=str(flag.id),
        flag_name=flag.flag_name,
        description=flag.description,
        is_enabled=flag.is_enabled,
        rollout_percentage=flag.rollout_percentage,
        target_roles=flag.target_roles,
        metadata=flag.metadata_,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


@app.delete("/flags/{flag_name}", status_code=204)
async def delete_flag(
    flag_name: str,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a feature flag. Admin only. Also deletes all overrides (cascade)."""
    repo = repository.FeatureFlagRepository(db)
    deleted = await repo.delete_flag(flag_name)
    if not deleted:
        raise not_found("FeatureFlag", flag_name)


@app.post("/flags/{flag_name}/overrides", response_model=schemas.OverrideResponse, status_code=201)
async def set_override(
    flag_name: str,
    body: schemas.OverrideRequest,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Set a user-specific override for a flag. Admin only."""
    repo = repository.FeatureFlagRepository(db)
    flag = await repo.get_by_name(flag_name)

    if not flag:
        raise not_found("FeatureFlag", flag_name)

    override = await repo.set_override(
        flag_id=str(flag.id),
        user_id=body.user_id,
        is_enabled=body.is_enabled,
        reason=body.reason,
    )

    return schemas.OverrideResponse(
        id=str(override.id),
        flag_name=flag_name,
        user_id=str(override.user_id),
        is_enabled=override.is_enabled,
        reason=override.reason,
        created_at=override.created_at,
    )


@app.delete("/flags/{flag_name}/overrides/{user_id}", status_code=204)
async def remove_override(
    flag_name: str,
    user_id: str,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user-specific override. Admin only."""
    repo = repository.FeatureFlagRepository(db)
    flag = await repo.get_by_name(flag_name)

    if not flag:
        raise not_found("FeatureFlag", flag_name)

    deleted = await repo.delete_override(str(flag.id), user_id)
    if not deleted:
        raise not_found("FlagOverride", f"flag={flag_name}, user={user_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=ff_config.settings.service_port,
        reload=ff_config.settings.debug,
    )
