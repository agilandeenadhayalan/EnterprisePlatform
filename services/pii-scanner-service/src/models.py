"""
Domain models for the PII scanner service.

Detects PII using regex patterns and provides masking capabilities.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class PIIType(str, Enum):
    """Types of PII that can be detected."""
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"


class PIIFinding:
    """A single PII detection finding."""

    def __init__(
        self,
        pii_type: str,
        value: str,
        start: int,
        end: int,
    ):
        self.pii_type = pii_type
        self.value = value
        self.start = start
        self.end = end

    def to_dict(self) -> dict:
        return {
            "pii_type": self.pii_type,
            "value": self.value,
            "start": self.start,
            "end": self.end,
        }


class ScanResult:
    """Result of a PII scan operation."""

    def __init__(
        self,
        id: str,
        source: str,
        text_length: int,
        findings: Optional[list[dict[str, Any]]] = None,
        scanned_at: Optional[datetime] = None,
    ):
        self.id = id
        self.source = source
        self.text_length = text_length
        self.findings = findings or []
        self.scanned_at = scanned_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "text_length": self.text_length,
            "findings": self.findings,
            "pii_count": len(self.findings),
            "scanned_at": self.scanned_at.isoformat(),
        }
