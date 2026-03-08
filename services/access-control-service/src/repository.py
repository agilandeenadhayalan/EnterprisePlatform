"""
Access-control service repository — database access layer.

Handles all SQL operations for roles and user-role assignments.
Permission checking uses JSONB queries and in-app wildcard matching.
"""

import fnmatch
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import RoleModel, UserRoleModel


class AccessControlRepository:
    """Database operations for the access-control service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- Role operations --

    async def list_roles(self) -> list[RoleModel]:
        """Return all roles."""
        result = await self.db.execute(select(RoleModel).order_by(RoleModel.name))
        return list(result.scalars().all())

    async def get_role_by_id(self, role_id: str) -> Optional[RoleModel]:
        """Find a role by UUID."""
        result = await self.db.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Optional[RoleModel]:
        """Find a role by name."""
        result = await self.db.execute(
            select(RoleModel).where(RoleModel.name == name)
        )
        return result.scalar_one_or_none()

    # -- User-role operations --

    async def get_user_roles(self, user_id: str) -> list[tuple[UserRoleModel, RoleModel]]:
        """Get all roles assigned to a user (with role details)."""
        result = await self.db.execute(
            select(UserRoleModel, RoleModel)
            .join(RoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(UserRoleModel.user_id == user_id)
        )
        return list(result.all())

    async def assign_role(
        self, user_id: str, role_id: str, assigned_by: Optional[str] = None
    ) -> UserRoleModel:
        """Assign a role to a user."""
        user_role = UserRoleModel(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        self.db.add(user_role)
        await self.db.flush()
        return user_role

    async def get_user_role(self, user_id: str, role_id: str) -> Optional[UserRoleModel]:
        """Check if a user already has a specific role."""
        result = await self.db.execute(
            select(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role_id,
            )
        )
        return result.scalar_one_or_none()

    async def remove_role(self, user_id: str, role_id: str) -> bool:
        """Remove a role from a user. Returns True if a row was deleted."""
        result = await self.db.execute(
            delete(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role_id,
            )
        )
        return result.rowcount > 0

    # -- Permission checking --

    async def check_permission(self, user_id: str, permission: str) -> tuple[bool, Optional[str], list[str]]:
        """
        Check if a user has a specific permission through any of their roles.

        Supports wildcard matching: a role with "user:*" matches "user:read",
        "user:write", etc. Uses fnmatch for glob-style pattern matching.

        Returns:
            (allowed, role_name, permissions) — the granting role name and its
            full permissions list, or (False, None, []) if denied.
        """
        rows = await self.get_user_roles(user_id)

        for user_role, role in rows:
            perms = role.permissions or []
            for perm_pattern in perms:
                if fnmatch.fnmatch(permission, perm_pattern):
                    return True, role.name, perms

        return False, None, []
