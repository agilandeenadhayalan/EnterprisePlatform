"""
Domain models for the data quality service.

Supports rule types: completeness, freshness, accuracy, consistency, uniqueness.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class RuleType(str, Enum):
    """Types of data quality rules."""
    COMPLETENESS = "completeness"  # % non-null fields
    FRESHNESS = "freshness"  # Data age check
    ACCURACY = "accuracy"  # Value range check
    CONSISTENCY = "consistency"  # Cross-field validation
    UNIQUENESS = "uniqueness"  # No duplicate values


class QualityRule:
    """A data quality rule definition."""

    def __init__(
        self,
        id: str,
        dataset_id: str,
        name: str,
        rule_type: str,
        field: str,
        parameters: dict[str, Any],
        description: Optional[str] = None,
        severity: str = "warning",
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.dataset_id = dataset_id
        self.name = name
        self.rule_type = rule_type
        self.field = field
        self.parameters = parameters
        self.description = description or ""
        self.severity = severity  # info, warning, error, critical
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "field": self.field,
            "parameters": self.parameters,
            "description": self.description,
            "severity": self.severity,
            "created_at": self.created_at.isoformat(),
        }


class QualityResult:
    """Result of running a quality check."""

    def __init__(
        self,
        id: str,
        rule_id: str,
        dataset_id: str,
        status: str,
        message: str,
        actual_value: Optional[Any] = None,
        expected_value: Optional[Any] = None,
        checked_at: Optional[datetime] = None,
    ):
        self.id = id
        self.rule_id = rule_id
        self.dataset_id = dataset_id
        self.status = status  # passed, failed, error
        self.message = message
        self.actual_value = actual_value
        self.expected_value = expected_value
        self.checked_at = checked_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "dataset_id": self.dataset_id,
            "status": self.status,
            "message": self.message,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "checked_at": self.checked_at.isoformat(),
        }


class QualitySummary:
    """Summary of quality results for a dataset."""

    def __init__(
        self,
        dataset_id: str,
        total_rules: int,
        passed: int,
        failed: int,
        errors: int,
        score: float,
    ):
        self.dataset_id = dataset_id
        self.total_rules = total_rules
        self.passed = passed
        self.failed = failed
        self.errors = errors
        self.score = score

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "total_rules": self.total_rules,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "score": self.score,
        }
