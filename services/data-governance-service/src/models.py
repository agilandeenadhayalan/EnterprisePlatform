"""
Domain models for the data governance service.

Manages data classification levels and access policies.
Classification levels: public, internal, confidential, restricted.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ClassificationLevel(str, Enum):
    """Data classification levels from least to most restrictive."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class GovernancePolicy:
    """A data governance policy defining access rules."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        rules: list[dict[str, Any]],
        classification: str = "internal",
        enforcement: str = "advisory",
        owner: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.rules = rules  # list of policy rules
        self.classification = classification
        self.enforcement = enforcement  # advisory, mandatory
        self.owner = owner
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rules": self.rules,
            "classification": self.classification,
            "enforcement": self.enforcement,
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Classification:
    """A dataset classification record."""

    def __init__(
        self,
        dataset_id: str,
        level: str,
        reason: str,
        classified_by: Optional[str] = None,
        classified_at: Optional[datetime] = None,
        pii_fields: Optional[list[str]] = None,
        retention_days: Optional[int] = None,
    ):
        self.dataset_id = dataset_id
        self.level = level
        self.reason = reason
        self.classified_by = classified_by
        self.classified_at = classified_at or datetime.utcnow()
        self.pii_fields = pii_fields or []
        self.retention_days = retention_days

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "level": self.level,
            "reason": self.reason,
            "classified_by": self.classified_by,
            "classified_at": self.classified_at.isoformat(),
            "pii_fields": self.pii_fields,
            "retention_days": self.retention_days,
        }
