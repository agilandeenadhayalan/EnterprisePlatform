"""
Password hashing and JWT token creation.

This module contains the core security functions for the auth service.
The hash_password() and verify_password() functions are where a meaningful
design choice lives — the bcrypt cost factor balances security vs. latency.

TOKEN ARCHITECTURE:
- Access tokens: Short-lived (15 min), stateless, verified by any service
- Refresh tokens: Long-lived (7 days), stored in DB, can be revoked
- Token blacklist: Redis set of revoked JTIs (token IDs)
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config import settings


# ──────────────────────────────────────────────
# PASSWORD HASHING
# ──────────────────────────────────────────────
#
# TODO: This is your implementation opportunity!
#
# bcrypt cost factor trade-offs:
#   - rounds=10: ~100ms per hash (fast, less secure against brute force)
#   - rounds=12: ~300ms per hash (balanced — industry default)
#   - rounds=14: ~1.2s per hash (very secure, but adds login latency)
#
# Consider: This is a ride-hailing app. Drivers log in multiple times
# per day. How much latency is acceptable at login?
# ──────────────────────────────────────────────


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    The cost factor (rounds) determines how computationally expensive
    the hash is. Higher = more secure against brute force, but slower.

    Args:
        plain_password: The user's plaintext password

    Returns:
        Bcrypt hash string (includes salt and cost factor)
    """
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    This is constant-time to prevent timing attacks — bcrypt.checkpw
    always takes the same amount of time regardless of where the
    comparison fails.

    Args:
        plain_password: The password attempt
        hashed_password: The stored bcrypt hash

    Returns:
        True if the password matches
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ──────────────────────────────────────────────
# JWT TOKEN CREATION
# ──────────────────────────────────────────────


def create_access_token(user_id: str, email: str, role: str) -> tuple[str, int]:
    """
    Create a short-lived JWT access token.

    Returns:
        Tuple of (token_string, expires_in_seconds)
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.jwt_access_token_ttl_minutes)
    expires_at = now + expires_delta

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expires_at,
        "iat": now,
        "jti": str(uuid.uuid4()),  # Unique token ID for revocation
        "type": "access",
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """
    Create a long-lived refresh token.

    Refresh tokens are stored in the database (identity.user_sessions)
    and can be revoked individually or per-user.

    Returns:
        Tuple of (token_string, expires_at_datetime)
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.jwt_refresh_token_ttl_days)

    payload = {
        "sub": user_id,
        "exp": expires_at,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def create_token_pair(user_id: str, email: str, role: str) -> dict:
    """Create both access and refresh tokens."""
    access_token, expires_in = create_access_token(user_id, email, role)
    refresh_token, _ = create_refresh_token(user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }
