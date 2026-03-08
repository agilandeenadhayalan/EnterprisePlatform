"""
OTP service repository — database access layer.

Handles creating, querying, and updating OTP records.
OTP codes are always stored as SHA-256 hashes.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import OtpCodeModel


class OtpRepository:
    """Database operations for the OTP service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_otp(
        self,
        user_id: str,
        code_hash: str,
        channel: str,
        purpose: str,
        expires_at: datetime,
    ) -> OtpCodeModel:
        """Insert a new OTP record with the hashed code."""
        otp = OtpCodeModel(
            user_id=user_id,
            code_hash=code_hash,
            channel=channel,
            purpose=purpose,
            expires_at=expires_at,
        )
        self.db.add(otp)
        await self.db.flush()
        return otp

    async def get_pending_otp(self, user_id: str) -> Optional[OtpCodeModel]:
        """
        Get the most recent pending (non-expired, non-verified) OTP for a user.

        Returns None if no valid OTP exists.
        """
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(OtpCodeModel)
            .where(
                OtpCodeModel.user_id == user_id,
                OtpCodeModel.expires_at > now,
                OtpCodeModel.verified_at.is_(None),
            )
            .order_by(OtpCodeModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def increment_attempts(self, otp_id: str) -> None:
        """Increment the attempt counter for an OTP record."""
        await self.db.execute(
            update(OtpCodeModel)
            .where(OtpCodeModel.id == otp_id)
            .values(attempts=OtpCodeModel.attempts + 1)
        )

    async def mark_verified(self, otp_id: str) -> None:
        """Mark an OTP as verified (set verified_at timestamp)."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(OtpCodeModel)
            .where(OtpCodeModel.id == otp_id)
            .values(verified_at=now)
        )
