"""
Pydantic request/response schemas for the access-control service API.

Defines the shapes for role management and permission checking endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --

class CheckPermissionRequest(BaseModel):
    """POST /check-permission — check if a user has a specific permission."""
    user_id: str = Field(..., description="UUID of the user to check")
    permission: str = Field(..., description="Permission string, e.g. 'user:read' or 'ride:create'")


class AssignRoleRequest(BaseModel):
    """POST /users/{user_id}/roles — assign a role to a user."""
    role_id: str = Field(..., description="UUID of the role to assign")


# -- Response schemas --

class RoleResponse(BaseModel):
    """Role data returned from list and detail endpoints."""
    id: str
    name: str
    description: Optional[str] = None
    permissions: list[str] = []
    is_system: bool = False
    created_at: datetime


class CheckPermissionResponse(BaseModel):
    """Result of a permission check."""
    allowed: bool
    role: Optional[str] = None
    permissions: list[str] = []


class UserRoleResponse(BaseModel):
    """A role assigned to a user."""
    id: str
    role_id: str
    role_name: str
    assigned_at: datetime


class MessageResponse(BaseModel):
    """Simple acknowledgement response."""
    message: str
