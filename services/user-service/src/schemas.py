"""
Pydantic request/response schemas for the user service API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# -- Response schemas --

class UserResponse(BaseModel):
    """Public user data — never includes password_hash."""
    id: str
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserListResponse(BaseModel):
    """Paginated list of users."""
    items: list[UserResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False


# -- Request schemas --

class UpdateUserRequest(BaseModel):
    """PATCH /users/{user_id} — partial update of user fields."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
