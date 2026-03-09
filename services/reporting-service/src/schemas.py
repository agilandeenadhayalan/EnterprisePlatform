"""
Pydantic request/response schemas for the reporting API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class ReportGenerateRequest(BaseModel):
    """POST /reports/generate — generate a new report."""
    report_type: str = Field(..., description="Report type ID (e.g., daily_summary)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Report parameters")
    format: str = Field(default="json", description="Output format (json, csv, pdf)")


# ── Response schemas ──


class ReportTypeResponse(BaseModel):
    """Available report type definition."""
    type_id: str
    name: str
    description: str
    required_params: list[str]
    optional_params: list[str]
    supported_formats: list[str]


class ReportTypeListResponse(BaseModel):
    """List of available report types."""
    report_types: list[ReportTypeResponse]
    total: int


class ReportResultResponse(BaseModel):
    """Report generation result."""
    summary: dict[str, Any]
    row_count: int
    generated_at: str


class ReportResponse(BaseModel):
    """Full report record."""
    id: str
    report_type: str
    status: str
    parameters: dict[str, Any]
    format: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[ReportResultResponse] = None


class ReportListResponse(BaseModel):
    """List of reports."""
    reports: list[ReportResponse]
    total: int
