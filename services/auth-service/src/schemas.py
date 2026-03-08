"""
Pydantic request/response schemas for the auth service API.

These are the shapes that clients send and receive. They are deliberately
different from ORM models — never expose password_hash in responses!
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Request schemas ──

class RegisterRequest(BaseModel):
    """POST /register — create a new user account."""
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=128, description="At least 8 characters")
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


class LoginRequest(BaseModel):
    """POST /login — authenticate with email and password."""
    email: str
    password: str


class RefreshRequest(BaseModel):
    """POST /refresh — exchange a refresh token for new token pair."""
    refresh_token: str


# ── Response schemas ──

class TokenResponse(BaseModel):
    """Returned on successful login or refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires


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


class RegisterResponse(BaseModel):
    """POST /register response — user data + tokens."""
    user: UserResponse
    tokens: TokenResponse
    message: str = "Registration successful"
