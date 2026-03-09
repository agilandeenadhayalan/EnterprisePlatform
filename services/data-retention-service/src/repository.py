"""
Data Retention repository — in-memory policy and enforcement tracking.

Simulates TTL enforcement on ClickHouse tables and MinIO buckets.
"""

import random
import uuid
from datetime import datetime
from typing import Optional

from models import RetentionPolicy, RetentionRun


class RetentionRepository:
    """In-memory retention policies and enforcement results."""

    def __init__(self):
        self._policies: dict[str, RetentionPolicy] = {}
        self._runs: list[RetentionRun] = []

    # ── Policy CRUD ──

    def create_policy(
        self,
        name: str,
        target: str,
        target_type: str,
        retention_days: int,
        description: Optional[str] = None,
        enabled: bool = True,
    ) -> RetentionPolicy:
        """Create a new retention policy."""
        policy_id = str(uuid.uuid4())
        policy = RetentionPolicy(
            id=policy_id,
            name=name,
            target=target,
            target_type=target_type,
            retention_days=retention_days,
            description=description,
            enabled=enabled,
        )
        self._policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[RetentionPolicy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def list_policies(self) -> list[RetentionPolicy]:
        """List all retention policies."""
        return list(self._policies.values())

    def update_policy(self, policy_id: str, **fields) -> Optional[RetentionPolicy]:
        """Update specific fields on a policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(policy, key):
                setattr(policy, key, value)
        policy.updated_at = datetime.utcnow()
        return policy

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    # ── Enforcement ──

    def enforce_policies(self) -> list[RetentionRun]:
        """
        Run retention enforcement for all enabled policies.

        Simulates checking each policy's target and deleting expired data.
        """
        runs: list[RetentionRun] = []

        for policy in self._policies.values():
            if not policy.enabled:
                continue

            # Simulate deletion results
            records_deleted = random.randint(0, 10000)
            bytes_reclaimed = records_deleted * random.randint(50, 200)

            run = RetentionRun(
                id=str(uuid.uuid4()),
                policy_id=policy.id,
                policy_name=policy.name,
                target=policy.target,
                records_deleted=records_deleted,
                bytes_reclaimed=bytes_reclaimed,
                status="completed",
            )
            self._runs.append(run)
            runs.append(run)

        return runs

    def get_stats(self) -> dict:
        """Get retention statistics."""
        policies = list(self._policies.values())
        enabled = sum(1 for p in policies if p.enabled)
        disabled = sum(1 for p in policies if not p.enabled)

        return {
            "total_policies": len(policies),
            "enabled_policies": enabled,
            "disabled_policies": disabled,
            "total_enforcement_runs": len(self._runs),
            "total_records_deleted": sum(r.records_deleted for r in self._runs),
            "total_bytes_reclaimed": sum(r.bytes_reclaimed for r in self._runs),
        }


# Singleton repository instance
repo = RetentionRepository()
