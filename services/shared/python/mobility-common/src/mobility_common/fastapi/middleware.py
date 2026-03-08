"""
JWT authentication and RBAC middleware.

WHY middleware instead of per-route checks? Authentication is a cross-cutting
concern — nearly every endpoint needs it. By implementing it as FastAPI
dependencies, we:
1. Avoid repeating auth logic in every route handler
2. Get consistent behavior (same error format, same token parsing)
3. Can compose auth + RBAC: Depends(require_role("admin"))

SECURITY MODEL:
- JWT access tokens are short-lived (15 min default)
- Refresh tokens are longer-lived (7 days) and stored in user_sessions
- Token revocation uses a Redis blacklist (checked on every request)
- RBAC maps roles to permissions (e.g., admin can delete users)
"""

from typing import Any, Optional

import jwt
from fastapi import Depends, Request
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from mobility_common.fastapi.errors import unauthorized, forbidden


class AuthSettings(BaseSettings):
    """JWT configuration loaded from environment variables."""
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    model_config = {"env_prefix": "", "extra": "ignore"}


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""
    sub: str              # User ID
    email: str
    role: str
    exp: int              # Expiration timestamp
    iat: int              # Issued-at timestamp
    jti: Optional[str] = None  # Token ID for revocation


_auth_settings: AuthSettings | None = None


def _get_auth_settings() -> AuthSettings:
    global _auth_settings
    if _auth_settings is None:
        _auth_settings = AuthSettings()
    return _auth_settings


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Raises ProblemDetail(401) if the token is invalid or expired.
    PyJWT automatically checks the 'exp' claim.
    """
    settings = _get_auth_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise unauthorized("Token has expired")
    except jwt.InvalidTokenError as e:
        raise unauthorized(f"Invalid token: {e}")


async def get_current_user(request: Request) -> TokenPayload:
    """
    FastAPI dependency that extracts and validates the JWT from the
    Authorization header.

    Usage:
        @app.get("/users/me")
        async def get_me(user: TokenPayload = Depends(get_current_user)):
            return {"user_id": user.sub, "role": user.role}
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise unauthorized("Missing or invalid Authorization header")

    token = auth_header[7:]  # Strip "Bearer "
    return decode_token(token)


async def require_auth(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """
    Alias for get_current_user — makes route signatures more readable.

    Usage:
        @app.delete("/users/{id}", dependencies=[Depends(require_auth)])
    """
    return user


def require_role(*allowed_roles: str):
    """
    Factory that creates a dependency requiring specific roles.

    This is a "dependency factory" — it returns a dependency function
    that FastAPI can inject. The closure captures the allowed_roles.

    Usage:
        @app.delete("/users/{id}")
        async def delete_user(
            user: TokenPayload = Depends(require_role("admin")),
        ):
            ...
    """
    async def _check_role(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if user.role not in allowed_roles:
            raise forbidden(
                f"Role '{user.role}' cannot access this resource. "
                f"Required: {', '.join(allowed_roles)}"
            )
        return user

    return _check_role
