"""
Pydantic request/response schemas for the data governance API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class PolicyCreate(BaseModel):
    """POST /governance/policies — create a governance policy."""
    name: str = Field(..., description="Policy name")
    description: str = Field(..., description="Policy description")
    rules: list[dict[str, Any]] = Field(..., description="Policy rules")
    classification: str = Field(default="internal", description="Classification level")
    enforcement: str = Field(default="advisory", description="Enforcement mode: advisory, mandatory")
    owner: Optional[str] = Field(default=None, description="Policy owner")


class PolicyUpdate(BaseModel):
    """PATCH /governance/policies/{id} — update a policy."""
    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[list[dict[str, Any]]] = None
    classification: Optional[str] = None
    enforcement: Optional[str] = None
    owner: Optional[str] = None


class ClassifyRequest(BaseModel):
    """POST /governance/classify/{dataset_id} — classify a dataset."""
    level: str = Field(..., description="Classification level: public, internal, confidential, restricted")
    reason: str = Field(..., description="Reason for classification")
    classified_by: Optional[str] = Field(default=None, description="Who classified")
    pii_fields: Optional[list[str]] = Field(default=None, description="Fields containing PII")
    retention_days: Optional[int] = Field(default=None, description="Retention period in days")


# ── Response schemas ──

class PolicyResponse(BaseModel):
    """A governance policy."""
    id: str
    name: str
    description: str
    rules: list[dict[str, Any]]
    classification: str
    enforcement: str
    owner: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ClassificationResponse(BaseModel):
    """A dataset classification."""
    dataset_id: str
    level: str
    reason: str
    classified_by: Optional[str] = None
    classified_at: datetime
    pii_fields: list[str] = []
    retention_days: Optional[int] = None


class ClassificationLevelResponse(BaseModel):
    """A classification level definition."""
    level: str
    description: str
    examples: list[str]
