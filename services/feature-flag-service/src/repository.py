"""
Feature flag service repository — database access layer.

Provides clean methods for CRUD on feature_flags and flag_overrides,
plus the critical evaluate_flag method that implements the decision tree:

  1. Check user-specific override → if exists, return override value
  2. Check if flag is globally enabled
  3. If enabled, check target_roles (user's role must match if specified)
  4. Check rollout_percentage using hash(user_id + flag_name) % 100
  5. Return the decision with a reason string
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import FeatureFlagModel, FlagOverrideModel


def compute_rollout_hash(user_id: str, flag_name: str) -> int:
    """
    Compute a deterministic hash for rollout percentage decisions.

    Uses SHA-256 of user_id + flag_name, then mod 100 to get a stable
    number between 0-99. This ensures:
      - Same user + flag always gets the same result (deterministic)
      - Different flags give different results for the same user
      - Distribution is roughly uniform across users
    """
    combined = f"{user_id}:{flag_name}"
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    return int.from_bytes(hash_bytes[:4], byteorder="big") % 100


class FeatureFlagRepository:
    """Database operations for the feature flag service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Flag CRUD ──

    async def list_flags(self) -> list[FeatureFlagModel]:
        """Return all feature flags, ordered by name."""
        result = await self.db.execute(
            select(FeatureFlagModel).order_by(FeatureFlagModel.flag_name)
        )
        return list(result.scalars().all())

    async def get_by_name(self, flag_name: str) -> Optional[FeatureFlagModel]:
        """Find a feature flag by its unique name."""
        result = await self.db.execute(
            select(FeatureFlagModel).where(FeatureFlagModel.flag_name == flag_name)
        )
        return result.scalar_one_or_none()

    async def create_flag(
        self,
        flag_name: str,
        description: Optional[str],
        is_enabled: bool,
        rollout_percentage: int,
        target_roles: Optional[list[str]],
        metadata: Optional[dict],
    ) -> FeatureFlagModel:
        """Create a new feature flag."""
        now = datetime.now(timezone.utc)
        flag = FeatureFlagModel(
            flag_name=flag_name,
            description=description,
            is_enabled=is_enabled,
            rollout_percentage=rollout_percentage,
            target_roles=target_roles,
            metadata_=metadata,
            created_at=now,
            updated_at=now,
        )
        self.db.add(flag)
        await self.db.flush()
        return flag

    async def update_flag(
        self,
        flag: FeatureFlagModel,
        description: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        rollout_percentage: Optional[int] = None,
        target_roles: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> FeatureFlagModel:
        """Update an existing flag's fields (only non-None values are applied)."""
        if description is not None:
            flag.description = description
        if is_enabled is not None:
            flag.is_enabled = is_enabled
        if rollout_percentage is not None:
            flag.rollout_percentage = rollout_percentage
        if target_roles is not None:
            flag.target_roles = target_roles
        if metadata is not None:
            flag.metadata_ = metadata

        flag.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return flag

    async def delete_flag(self, flag_name: str) -> bool:
        """Delete a flag by name. Returns True if deleted."""
        result = await self.db.execute(
            delete(FeatureFlagModel).where(FeatureFlagModel.flag_name == flag_name)
        )
        return result.rowcount > 0

    # ── Override operations ──

    async def get_override(self, flag_id: str, user_id: str) -> Optional[FlagOverrideModel]:
        """Find a user-specific override for a flag."""
        result = await self.db.execute(
            select(FlagOverrideModel).where(
                FlagOverrideModel.flag_id == flag_id,
                FlagOverrideModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def set_override(
        self,
        flag_id: str,
        user_id: str,
        is_enabled: bool,
        reason: Optional[str],
    ) -> FlagOverrideModel:
        """
        Set a user-specific override for a flag.

        If an override already exists for this user+flag, replaces it.
        """
        existing = await self.get_override(flag_id, user_id)
        if existing:
            existing.is_enabled = is_enabled
            existing.reason = reason
            await self.db.flush()
            return existing

        override = FlagOverrideModel(
            flag_id=flag_id,
            user_id=user_id,
            is_enabled=is_enabled,
            reason=reason,
        )
        self.db.add(override)
        await self.db.flush()
        return override

    async def delete_override(self, flag_id: str, user_id: str) -> bool:
        """Remove a user-specific override. Returns True if deleted."""
        result = await self.db.execute(
            delete(FlagOverrideModel).where(
                FlagOverrideModel.flag_id == flag_id,
                FlagOverrideModel.user_id == user_id,
            )
        )
        return result.rowcount > 0

    # ── Flag evaluation ──

    async def evaluate_flag(
        self, flag_name: str, user_id: str, user_role: str
    ) -> tuple[bool, str]:
        """
        Evaluate whether a flag is enabled for a specific user.

        Decision tree:
          1. Check user-specific override → if exists, return override value
          2. Check if flag is globally enabled → if not, return False
          3. If enabled, check target_roles → user's role must match
          4. Check rollout_percentage → hash(user_id + flag_name) % 100
          5. Return (is_enabled, reason_string)
        """
        flag = await self.get_by_name(flag_name)
        if not flag:
            return False, f"flag '{flag_name}' not found"

        # Step 1: Check user-specific override
        override = await self.get_override(str(flag.id), user_id)
        if override:
            status = "enabled" if override.is_enabled else "disabled"
            return override.is_enabled, f"user override: {status}"

        # Step 2: Check global enabled state
        if not flag.is_enabled:
            return False, "flag is globally disabled"

        # Step 3: Check target roles (if specified)
        if flag.target_roles and len(flag.target_roles) > 0:
            if user_role not in flag.target_roles:
                return False, f"user role '{user_role}' not in target roles"

        # Step 4: Check rollout percentage
        if flag.rollout_percentage < 100:
            hash_value = compute_rollout_hash(user_id, flag_name)
            if hash_value < flag.rollout_percentage:
                return True, f"user included in {flag.rollout_percentage}% rollout (hash={hash_value})"
            else:
                return False, f"user excluded from {flag.rollout_percentage}% rollout (hash={hash_value})"

        # Step 5: Flag is enabled, no restrictions
        return True, "flag enabled, no restrictions"
