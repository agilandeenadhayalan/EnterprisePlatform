"""
Data Governance repository — in-memory policy and classification storage.

Manages governance policies and dataset classifications.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import GovernancePolicy, Classification, ClassificationLevel


# Classification level definitions
CLASSIFICATION_LEVELS = [
    {
        "level": "public",
        "description": "Data that is freely available and poses no risk if disclosed",
        "examples": ["Service status pages", "Public transit schedules", "Open API documentation"],
    },
    {
        "level": "internal",
        "description": "Data for internal use only, not intended for public disclosure",
        "examples": ["Internal metrics", "Employee directories", "Development logs"],
    },
    {
        "level": "confidential",
        "description": "Sensitive data requiring protection, limited access",
        "examples": ["User emails", "Payment amounts", "Driver ratings"],
    },
    {
        "level": "restricted",
        "description": "Highly sensitive data with strict access controls and audit requirements",
        "examples": ["SSN/national IDs", "Credit card numbers", "Medical records"],
    },
]


class GovernanceRepository:
    """In-memory governance policies and classifications storage."""

    def __init__(self):
        self._policies: dict[str, GovernancePolicy] = {}
        self._classifications: dict[str, Classification] = {}  # dataset_id -> classification

    # ── Policy CRUD ──

    def create_policy(
        self,
        name: str,
        description: str,
        rules: list[dict[str, Any]],
        classification: str = "internal",
        enforcement: str = "advisory",
        owner: Optional[str] = None,
    ) -> GovernancePolicy:
        """Create a new governance policy."""
        policy_id = str(uuid.uuid4())
        policy = GovernancePolicy(
            id=policy_id,
            name=name,
            description=description,
            rules=rules,
            classification=classification,
            enforcement=enforcement,
            owner=owner,
        )
        self._policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[GovernancePolicy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def list_policies(self) -> list[GovernancePolicy]:
        """List all policies."""
        return list(self._policies.values())

    def update_policy(self, policy_id: str, **fields) -> Optional[GovernancePolicy]:
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

    # ── Classification ──

    def classify_dataset(
        self,
        dataset_id: str,
        level: str,
        reason: str,
        classified_by: Optional[str] = None,
        pii_fields: Optional[list[str]] = None,
        retention_days: Optional[int] = None,
    ) -> Classification:
        """Classify a dataset with a specific level."""
        valid_levels = [l.value for l in ClassificationLevel]
        if level not in valid_levels:
            raise ValueError(f"Invalid level: {level}. Must be one of: {', '.join(valid_levels)}")

        classification = Classification(
            dataset_id=dataset_id,
            level=level,
            reason=reason,
            classified_by=classified_by,
            pii_fields=pii_fields,
            retention_days=retention_days,
        )
        self._classifications[dataset_id] = classification
        return classification

    def get_classification(self, dataset_id: str) -> Optional[Classification]:
        """Get classification for a dataset."""
        return self._classifications.get(dataset_id)

    def get_classification_levels(self) -> list[dict]:
        """Get all classification level definitions."""
        return CLASSIFICATION_LEVELS


# Singleton repository instance
repo = GovernanceRepository()
