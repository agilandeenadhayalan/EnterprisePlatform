"""
Pydantic request/response schemas for the data quality API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class QualityRuleCreate(BaseModel):
    """POST /quality/rules — create a quality rule."""
    dataset_id: str = Field(..., description="Dataset this rule applies to")
    name: str = Field(..., description="Rule name")
    rule_type: str = Field(..., description="Rule type: completeness, freshness, accuracy, consistency, uniqueness")
    field: str = Field(..., description="Field/column to check")
    parameters: dict[str, Any] = Field(..., description="Rule parameters (e.g., {min_completeness: 0.95})")
    description: Optional[str] = Field(default=None, description="Rule description")
    severity: str = Field(default="warning", description="Severity: info, warning, error, critical")


class QualityRuleUpdate(BaseModel):
    """PATCH /quality/rules/{id} — update a quality rule."""
    name: Optional[str] = None
    rule_type: Optional[str] = None
    field: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    severity: Optional[str] = None


class QualityRunRequest(BaseModel):
    """POST /quality/run — run quality checks for a dataset."""
    dataset_id: str = Field(..., description="Dataset to check")
    sample_data: list[dict[str, Any]] = Field(..., description="Sample data rows to validate")


# ── Response schemas ──

class QualityRuleResponse(BaseModel):
    """A quality rule."""
    id: str
    dataset_id: str
    name: str
    rule_type: str
    field: str
    parameters: dict[str, Any]
    description: str = ""
    severity: str
    created_at: datetime


class QualityResultResponse(BaseModel):
    """A quality check result."""
    id: str
    rule_id: str
    dataset_id: str
    status: str
    message: str
    actual_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    checked_at: datetime


class QualityRunResponse(BaseModel):
    """Response from running quality checks."""
    dataset_id: str
    results: list[QualityResultResponse]
    passed: int
    failed: int
    errors: int


class QualitySummaryResponse(BaseModel):
    """Quality summary for a dataset."""
    dataset_id: str
    total_rules: int
    passed: int
    failed: int
    errors: int
    score: float


class QualityResultListResponse(BaseModel):
    """List of quality results."""
    results: list[QualityResultResponse]
    total: int
