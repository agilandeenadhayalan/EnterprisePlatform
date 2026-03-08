"""
Auth Service — FastAPI application.

ROUTES:
  POST /register  — Create a new user account
  POST /login     — Authenticate and receive JWT tokens
  POST /refresh   — Exchange refresh token for new token pair
  POST /logout    — Revoke refresh token (logout current device)
  POST /logout/all — Revoke all sessions (logout everywhere)
  GET  /me        — Get current authenticated user
  GET  /health    — Health check (provided by create_app)

This is the REFERENCE implementation for all Python services in the platform.
Every other FastAPI service follows this exact structure:
  config.py → models.py → schemas.py → repository.py → main.py
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import conflict, not_found, unauthorized
from mobility_common.fastapi.middleware import get_current_user, TokenPayload

# Rename to avoid circular import issues — use absolute module names
import config as auth_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository
import security


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(auth_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Auth Service",
    version="0.1.0",
    description="Authentication and JWT token management for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/register", response_model=schemas.RegisterResponse, status_code=201)
async def register(
    body: schemas.RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user account.

    1. Check if email already exists (→ 409 Conflict)
    2. Hash password with bcrypt
    3. Insert user record
    4. Create session + token pair
    5. Return user data + tokens
    """
    repo = repository.AuthRepository(db)

    # Check for duplicate email
    existing = await repo.get_user_by_email(body.email)
    if existing:
        raise conflict(f"Email '{body.email}' is already registered")

    # Hash password and create user
    password_hash = security.hash_password(body.password)
    user = await repo.create_user(
        email=body.email,
        full_name=body.full_name,
        password_hash=password_hash,
        phone=body.phone,
    )

    # Create token pair
    tokens = security.create_token_pair(str(user.id), user.email, user.role)

    # Store refresh token as session
    _, expires_at = security.create_refresh_token(str(user.id))
    await repo.create_session(
        user_id=str(user.id),
        refresh_token=tokens["refresh_token"],
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
    )

    return schemas.RegisterResponse(
        user=schemas.UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            phone=user.phone,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
        tokens=schemas.TokenResponse(**tokens),
    )


@app.post("/login", response_model=schemas.TokenResponse)
async def login(
    body: schemas.LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email and password.

    Returns a JWT access token (short-lived) and refresh token (long-lived).
    The access token is used in Authorization headers for all API requests.
    """
    repo = repository.AuthRepository(db)

    # Find user
    user = await repo.get_user_by_email(body.email)
    if not user:
        raise unauthorized("Invalid email or password")

    # Verify password
    if not security.verify_password(body.password, user.password_hash):
        raise unauthorized("Invalid email or password")

    # Check if account is active
    if not user.is_active:
        raise unauthorized("Account is deactivated")

    # Create tokens
    tokens = security.create_token_pair(str(user.id), user.email, user.role)

    # Store session
    _, expires_at = security.create_refresh_token(str(user.id))
    await repo.create_session(
        user_id=str(user.id),
        refresh_token=tokens["refresh_token"],
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
    )

    return schemas.TokenResponse(**tokens)


@app.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_token(
    body: schemas.RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new token pair.

    The old refresh token is revoked (one-time use). This is "token rotation" —
    if a refresh token is stolen, the legitimate user's next refresh attempt
    will fail (because the stolen token was already used), signaling compromise.
    """
    repo = repository.AuthRepository(db)

    # Find the session with this refresh token
    session = await repo.get_session_by_token(body.refresh_token)
    if not session:
        raise unauthorized("Invalid or expired refresh token")

    # Get the user
    user = await repo.get_user_by_id(str(session.user_id))
    if not user or not user.is_active:
        raise unauthorized("User not found or deactivated")

    # Revoke old session (one-time use)
    await repo.delete_session(str(session.id))

    # Create new token pair
    tokens = security.create_token_pair(str(user.id), user.email, user.role)

    # Store new session
    _, expires_at = security.create_refresh_token(str(user.id))
    await repo.create_session(
        user_id=str(user.id),
        refresh_token=tokens["refresh_token"],
        expires_at=expires_at,
    )

    return schemas.TokenResponse(**tokens)


@app.post("/logout", status_code=204)
async def logout(
    body: schemas.RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific refresh token (logout current device)."""
    repo = repository.AuthRepository(db)
    session = await repo.get_session_by_token(body.refresh_token)
    if session:
        await repo.delete_session(str(session.id))


@app.post("/logout/all", status_code=204)
async def logout_all(
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all sessions for the current user (logout everywhere)."""
    repo = repository.AuthRepository(db)
    await repo.delete_user_sessions(user.sub)


@app.get("/me", response_model=schemas.UserResponse)
async def get_me(
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the currently authenticated user's profile."""
    repo = repository.AuthRepository(db)
    db_user = await repo.get_user_by_id(user.sub)
    if not db_user:
        raise not_found("User", user.sub)

    return schemas.UserResponse(
        id=str(db_user.id),
        email=db_user.email,
        full_name=db_user.full_name,
        role=db_user.role,
        phone=db_user.phone,
        is_active=db_user.is_active,
        is_verified=db_user.is_verified,
        created_at=db_user.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=auth_config.settings.service_port,
        reload=auth_config.settings.debug,
    )
