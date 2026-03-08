"""
Access Control Service — FastAPI application.

ROUTES:
  GET    /roles                      — List all roles
  GET    /roles/{role_id}            — Get role details with permissions
  POST   /check-permission           — Check if a user has a specific permission
  GET    /users/{user_id}/roles      — Get roles assigned to a user
  POST   /users/{user_id}/roles      — Assign a role to a user (admin only)
  DELETE /users/{user_id}/roles/{role_id} — Remove a role (admin only)
  GET    /health                     — Health check (provided by create_app)
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
from mobility_common.fastapi.errors import not_found, conflict
from mobility_common.fastapi.middleware import get_current_user, require_role, TokenPayload

import config as acl_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(acl_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Access Control Service",
    version="0.1.0",
    description="RBAC and permission checking for Smart Mobility Platform",
    lifespan=lifespan,
)


# -- Routes --


@app.get("/roles", response_model=list[schemas.RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db)):
    """List all available roles."""
    repo = repository.AccessControlRepository(db)
    roles = await repo.list_roles()
    return [
        schemas.RoleResponse(
            id=str(r.id),
            name=r.name,
            description=r.description,
            permissions=r.permissions or [],
            is_system=r.is_system,
            created_at=r.created_at,
        )
        for r in roles
    ]


@app.get("/roles/{role_id}", response_model=schemas.RoleResponse)
async def get_role(role_id: str, db: AsyncSession = Depends(get_db)):
    """Get role details including permissions."""
    repo = repository.AccessControlRepository(db)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise not_found("Role", role_id)
    return schemas.RoleResponse(
        id=str(role.id),
        name=role.name,
        description=role.description,
        permissions=role.permissions or [],
        is_system=role.is_system,
        created_at=role.created_at,
    )


@app.post("/check-permission", response_model=schemas.CheckPermissionResponse)
async def check_permission(
    body: schemas.CheckPermissionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a user has a specific permission.

    Scans all roles assigned to the user and checks if any role's permissions
    list matches the requested permission (supports wildcard patterns).
    """
    repo = repository.AccessControlRepository(db)
    allowed, role_name, permissions = await repo.check_permission(
        body.user_id, body.permission
    )
    return schemas.CheckPermissionResponse(
        allowed=allowed,
        role=role_name,
        permissions=permissions,
    )


@app.get("/users/{user_id}/roles", response_model=list[schemas.UserRoleResponse])
async def get_user_roles(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all roles assigned to a user."""
    repo = repository.AccessControlRepository(db)
    rows = await repo.get_user_roles(user_id)
    return [
        schemas.UserRoleResponse(
            id=str(ur.id),
            role_id=str(ur.role_id),
            role_name=role.name,
            assigned_at=ur.assigned_at,
        )
        for ur, role in rows
    ]


@app.post("/users/{user_id}/roles", response_model=schemas.UserRoleResponse, status_code=201)
async def assign_role(
    user_id: str,
    body: schemas.AssignRoleRequest,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Assign a role to a user (admin only)."""
    repo = repository.AccessControlRepository(db)

    # Verify role exists
    role = await repo.get_role_by_id(body.role_id)
    if not role:
        raise not_found("Role", body.role_id)

    # Check for duplicate assignment
    existing = await repo.get_user_role(user_id, body.role_id)
    if existing:
        raise conflict(f"User '{user_id}' already has role '{role.name}'")

    user_role = await repo.assign_role(
        user_id=user_id,
        role_id=body.role_id,
        assigned_by=admin.sub,
    )
    return schemas.UserRoleResponse(
        id=str(user_role.id),
        role_id=str(user_role.role_id),
        role_name=role.name,
        assigned_at=user_role.assigned_at,
    )


@app.delete("/users/{user_id}/roles/{role_id}", status_code=204)
async def remove_role(
    user_id: str,
    role_id: str,
    admin: TokenPayload = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a role from a user (admin only)."""
    repo = repository.AccessControlRepository(db)
    deleted = await repo.remove_role(user_id, role_id)
    if not deleted:
        raise not_found("UserRole", f"user={user_id}, role={role_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=acl_config.settings.service_port,
        reload=acl_config.settings.debug,
    )
