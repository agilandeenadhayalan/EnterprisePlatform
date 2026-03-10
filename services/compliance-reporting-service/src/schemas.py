"""
Pydantic request/response schemas for the compliance reporting API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class ReportCreate(BaseModel):
    """POST /compliance/reports — generate a new compliance report."""
    report_type: str = Field(..., description="Report type (e.g. audit, assessment)")
    framework: str = Field(..., description="Regulatory framework: SOC2, ISO27001, GDPR, HIPAA")
    generated_by: Optional[str] = Field(default=None, description="Who generated the report")
    period_start: Optional[str] = Field(default=None, description="Reporting period start date")
    period_end: Optional[str] = Field(default=None, description="Reporting period end date")


class ReportUpdate(BaseModel):
    """PATCH /compliance/reports/{id} — update report."""
    status: Optional[str] = None
    score: Optional[float] = None
    findings: Optional[list[dict[str, Any]]] = None


class FindingCreate(BaseModel):
    """POST /compliance/reports/{id}/findings — add finding."""
    category: str = Field(..., description="Finding category")
    description: str = Field(..., description="Finding description")
    severity: str = Field(default="medium", description="Severity: low, medium, high, critical")
    remediation: Optional[str] = Field(default=None, description="Recommended remediation")
    status: str = Field(default="open", description="Finding status")


# ── Response schemas ──

class FindingResponse(BaseModel):
    """A compliance finding."""
    id: str
    category: str
    description: str
    severity: str
    remediation: Optional[str] = None
    status: str


class ReportResponse(BaseModel):
    """A compliance report."""
    id: str
    report_type: str
    framework: str
    status: str
    generated_by: Optional[str] = None
    findings: list[dict[str, Any]] = []
    score: Optional[float] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FrameworkResponse(BaseModel):
    """A supported compliance framework."""
    name: str
    description: str
    categories: list[str]
