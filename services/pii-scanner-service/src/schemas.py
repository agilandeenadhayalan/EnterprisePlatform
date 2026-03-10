"""
Pydantic request/response schemas for the PII scanner API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class ScanTextRequest(BaseModel):
    """POST /pii/scan — scan text for PII."""
    text: str = Field(..., description="Text content to scan for PII")
    source: str = Field(default="manual", description="Source identifier")


class ScanDatasetRequest(BaseModel):
    """POST /pii/scan-dataset — scan a named dataset."""
    dataset_name: str = Field(..., description="Name of the dataset to scan")
    sample_data: list[str] = Field(..., description="Sample data rows to scan")


class MaskRequest(BaseModel):
    """POST /pii/mask — mask PII in text."""
    text: str = Field(..., description="Text content to mask")
    strategy: str = Field(default="redact", description="Masking strategy: redact, partial, hash")


# ── Response schemas ──

class PIIFindingResponse(BaseModel):
    """A PII finding."""
    pii_type: str
    value: str
    start: int
    end: int


class ScanResponse(BaseModel):
    """PII scan result."""
    id: str
    source: str
    text_length: int
    findings: list[dict[str, Any]] = []
    pii_count: int = 0
    scanned_at: datetime


class MaskResponse(BaseModel):
    """Masked text result."""
    original_length: int
    masked_text: str
    masked_count: int
    strategy: str


class PatternResponse(BaseModel):
    """A PII detection pattern."""
    pii_type: str
    description: str
    example: str
