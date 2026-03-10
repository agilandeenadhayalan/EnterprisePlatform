"""
Domain models for the compliance reporting service.

Generates compliance reports against regulatory frameworks (SOC2, ISO27001, GDPR, HIPAA).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ReportStatus(str, Enum):
    """Compliance report statuses."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Finding:
    """A compliance finding within a report."""

    def __init__(
        self,
        id: str,
        category: str,
        description: str,
        severity: str = "medium",
        remediation: Optional[str] = None,
        status: str = "open",
    ):
        self.id = id
        self.category = category
        self.description = description
        self.severity = severity
        self.remediation = remediation
        self.status = status

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "remediation": self.remediation,
            "status": self.status,
        }


class ComplianceReport:
    """A compliance report against a regulatory framework."""

    def __init__(
        self,
        id: str,
        report_type: str,
        framework: str,
        status: str = "draft",
        generated_by: Optional[str] = None,
        findings: Optional[list[dict[str, Any]]] = None,
        score: Optional[float] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.report_type = report_type
        self.framework = framework
        self.status = status
        self.generated_by = generated_by
        self.findings = findings or []
        self.score = score
        self.period_start = period_start
        self.period_end = period_end
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_type": self.report_type,
            "framework": self.framework,
            "status": self.status,
            "generated_by": self.generated_by,
            "findings": self.findings,
            "score": self.score,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
