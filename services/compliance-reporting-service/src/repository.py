"""
Compliance Reporting repository — in-memory report storage.

Manages compliance reports and findings against regulatory frameworks.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import ComplianceReport, ReportStatus


# Supported regulatory frameworks
FRAMEWORKS = [
    {
        "name": "SOC2",
        "description": "Service Organization Control 2 — trust services criteria",
        "categories": ["Security", "Availability", "Processing Integrity", "Confidentiality", "Privacy"],
    },
    {
        "name": "ISO27001",
        "description": "Information security management system standard",
        "categories": ["Access Control", "Cryptography", "Physical Security", "Operations Security", "Compliance"],
    },
    {
        "name": "GDPR",
        "description": "General Data Protection Regulation — EU data privacy",
        "categories": ["Lawful Basis", "Data Subject Rights", "Data Protection", "Breach Notification", "DPO"],
    },
    {
        "name": "HIPAA",
        "description": "Health Insurance Portability and Accountability Act",
        "categories": ["Privacy Rule", "Security Rule", "Breach Notification", "Enforcement"],
    },
]


class ComplianceRepository:
    """In-memory compliance reports storage."""

    def __init__(self):
        self._reports: dict[str, ComplianceReport] = {}

    # ── Report CRUD ──

    def create_report(
        self,
        report_type: str,
        framework: str,
        generated_by: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> ComplianceReport:
        """Generate a new compliance report."""
        report_id = str(uuid.uuid4())
        report = ComplianceReport(
            id=report_id,
            report_type=report_type,
            framework=framework,
            generated_by=generated_by,
            period_start=period_start,
            period_end=period_end,
        )
        self._reports[report_id] = report
        return report

    def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        """Get a report by ID."""
        return self._reports.get(report_id)

    def list_reports(
        self,
        framework: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[ComplianceReport]:
        """List all reports, optionally filtered."""
        reports = list(self._reports.values())
        if framework:
            reports = [r for r in reports if r.framework == framework]
        if status:
            reports = [r for r in reports if r.status == status]
        return reports

    def update_report(self, report_id: str, **fields) -> Optional[ComplianceReport]:
        """Update specific fields on a report."""
        report = self._reports.get(report_id)
        if not report:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(report, key):
                setattr(report, key, value)
        report.updated_at = datetime.utcnow()
        return report

    def delete_report(self, report_id: str) -> bool:
        """Delete a report."""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False

    # ── Findings ──

    def add_finding(
        self,
        report_id: str,
        category: str,
        description: str,
        severity: str = "medium",
        remediation: Optional[str] = None,
        status: str = "open",
    ) -> Optional[dict]:
        """Add a finding to a report."""
        report = self._reports.get(report_id)
        if not report:
            return None
        finding = {
            "id": str(uuid.uuid4()),
            "category": category,
            "description": description,
            "severity": severity,
            "remediation": remediation,
            "status": status,
        }
        report.findings.append(finding)
        report.updated_at = datetime.utcnow()
        return finding

    # ── Frameworks ──

    def get_frameworks(self) -> list[dict]:
        """Get all supported compliance frameworks."""
        return FRAMEWORKS


# Singleton repository instance
repo = ComplianceRepository()
