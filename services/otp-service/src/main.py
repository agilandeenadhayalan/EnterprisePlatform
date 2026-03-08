"""
OTP Service — FastAPI application.

ROUTES:
  POST /otp/send             — Generate and "send" an OTP (stores it; actual sending is mocked)
  POST /otp/verify           — Verify an OTP code
  GET  /otp/status/{user_id} — Check if a user has a pending OTP
  GET  /health               — Health check (provided by create_app)

OTP SECURITY:
- Codes are generated using secrets.token_hex() for cryptographic randomness
- Only the SHA-256 hash is stored in the database
- Verification compares hashes (never stores plaintext)
- Codes expire after otp_ttl_minutes (default: 10 minutes)
- Max 3 attempts per OTP before it becomes invalid
"""

import hashlib
import secrets
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import unauthorized, not_found

import config as otp_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


def generate_otp_code(length: int = 6) -> str:
    """
    Generate a cryptographically secure numeric OTP code.

    Uses secrets.token_hex() for randomness, then converts to a numeric
    string of the specified length. This ensures the code is suitable
    for SMS/email delivery (digits only).
    """
    # Generate enough random bytes, convert to integer, take modulo for length
    raw = secrets.token_hex(16)
    numeric = int(raw, 16) % (10 ** length)
    return str(numeric).zfill(length)


def hash_otp(code: str) -> str:
    """Hash an OTP code with SHA-256 before storing."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(otp_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="OTP Service",
    version="0.1.0",
    description="One-time passcode generation and verification for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/otp/send", response_model=schemas.SendOtpResponse, status_code=201)
async def send_otp(
    body: schemas.SendOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate and "send" an OTP code.

    In production, this would integrate with an email/SMS provider.
    For now, it generates the code, hashes it, and stores it in the database.
    The plaintext code would be sent via the chosen channel.
    """
    repo = repository.OtpRepository(db)

    # Generate OTP
    code = generate_otp_code(otp_config.settings.otp_length)
    code_hash = hash_otp(code)

    # Calculate expiration
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=otp_config.settings.otp_ttl_minutes
    )

    # Store hashed OTP
    await repo.create_otp(
        user_id=body.user_id,
        code_hash=code_hash,
        channel=body.channel,
        purpose=body.purpose,
        expires_at=expires_at,
    )

    # In production: send code via email/SMS here
    # For development: the code would be logged or returned in a dev-only field

    return schemas.SendOtpResponse(
        channel=body.channel,
        expires_in_minutes=otp_config.settings.otp_ttl_minutes,
    )


@app.post("/otp/verify", response_model=schemas.VerifyOtpResponse)
async def verify_otp(
    body: schemas.VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify an OTP code submitted by the user.

    The submitted code is hashed and compared against the stored hash.
    Max attempts are enforced — after 3 failed attempts, the OTP is invalid.
    """
    repo = repository.OtpRepository(db)

    # Find pending OTP for user
    otp = await repo.get_pending_otp(body.user_id)
    if not otp:
        return schemas.VerifyOtpResponse(
            verified=False,
            message="No pending OTP found or OTP has expired",
        )

    # Check max attempts
    if otp.attempts >= otp.max_attempts:
        return schemas.VerifyOtpResponse(
            verified=False,
            message="Maximum verification attempts exceeded",
        )

    # Hash the submitted code and compare
    submitted_hash = hash_otp(body.code)

    if submitted_hash != otp.code_hash:
        # Increment attempt counter
        await repo.increment_attempts(str(otp.id))
        remaining = otp.max_attempts - otp.attempts - 1
        return schemas.VerifyOtpResponse(
            verified=False,
            message=f"Invalid OTP code. {remaining} attempts remaining",
        )

    # Success — mark as verified
    await repo.mark_verified(str(otp.id))
    return schemas.VerifyOtpResponse(
        verified=True,
        message="OTP verified successfully",
    )


@app.get("/otp/status/{user_id}", response_model=schemas.OtpStatusResponse)
async def get_otp_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if a user has a pending (non-expired, non-verified) OTP."""
    repo = repository.OtpRepository(db)
    otp = await repo.get_pending_otp(user_id)

    if not otp:
        return schemas.OtpStatusResponse(has_pending_otp=False)

    return schemas.OtpStatusResponse(
        has_pending_otp=True,
        channel=otp.channel,
        purpose=otp.purpose,
        expires_at=otp.expires_at,
        attempts_remaining=otp.max_attempts - otp.attempts,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=otp_config.settings.service_port,
        reload=otp_config.settings.debug,
    )
