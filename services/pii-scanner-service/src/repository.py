"""
PII Scanner repository — in-memory scan results and regex-based PII detection.

Contains regex patterns for detecting SSN, email, phone, credit card, and IP addresses.
"""

import hashlib
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from models import ScanResult, PIIFinding, PIIType


# PII detection regex patterns
PII_PATTERNS = {
    "ssn": {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "description": "US Social Security Number (XXX-XX-XXXX)",
        "example": "123-45-6789",
    },
    "email": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "description": "Email address",
        "example": "user@example.com",
    },
    "phone": {
        "pattern": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "description": "US phone number",
        "example": "(555) 123-4567",
    },
    "credit_card": {
        "pattern": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "description": "Credit card number (16 digits)",
        "example": "4111-1111-1111-1111",
    },
    "ip_address": {
        "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "description": "IPv4 address",
        "example": "192.168.1.1",
    },
}


class PIIScannerRepository:
    """In-memory PII scan results storage with regex-based detection."""

    def __init__(self):
        self._scan_results: dict[str, ScanResult] = {}

    def scan_text(self, text: str, source: str = "manual") -> ScanResult:
        """Scan text for PII using regex patterns."""
        findings = []
        for pii_type, config in PII_PATTERNS.items():
            for match in re.finditer(config["pattern"], text):
                findings.append({
                    "pii_type": pii_type,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })

        scan_id = str(uuid.uuid4())
        result = ScanResult(
            id=scan_id,
            source=source,
            text_length=len(text),
            findings=findings,
        )
        self._scan_results[scan_id] = result
        return result

    def scan_dataset(self, dataset_name: str, sample_data: list[str]) -> ScanResult:
        """Scan a named dataset's sample data for PII."""
        all_findings = []
        offset = 0
        for row in sample_data:
            for pii_type, config in PII_PATTERNS.items():
                for match in re.finditer(config["pattern"], row):
                    all_findings.append({
                        "pii_type": pii_type,
                        "value": match.group(),
                        "start": offset + match.start(),
                        "end": offset + match.end(),
                    })
            offset += len(row) + 1  # +1 for separator

        total_length = sum(len(row) for row in sample_data)
        scan_id = str(uuid.uuid4())
        result = ScanResult(
            id=scan_id,
            source=dataset_name,
            text_length=total_length,
            findings=all_findings,
        )
        self._scan_results[scan_id] = result
        return result

    def get_scan_result(self, scan_id: str) -> Optional[ScanResult]:
        """Get a scan result by ID."""
        return self._scan_results.get(scan_id)

    def list_scan_results(self) -> list[ScanResult]:
        """List all past scan results."""
        return list(self._scan_results.values())

    def mask_text(self, text: str, strategy: str = "redact") -> dict:
        """Mask PII in text using the specified strategy."""
        masked = text
        count = 0
        # Process patterns in reverse order of match positions to preserve offsets
        all_matches = []
        for pii_type, config in PII_PATTERNS.items():
            for match in re.finditer(config["pattern"], text):
                all_matches.append((match.start(), match.end(), match.group(), pii_type))

        # Sort by position descending so replacements don't shift offsets
        all_matches.sort(key=lambda x: x[0], reverse=True)

        for start, end, value, pii_type in all_matches:
            if strategy == "redact":
                replacement = "[REDACTED]"
            elif strategy == "partial":
                replacement = "*" * (len(value) - 4) + value[-4:]
            elif strategy == "hash":
                replacement = hashlib.sha256(value.encode()).hexdigest()[:12]
            else:
                replacement = "[REDACTED]"
            masked = masked[:start] + replacement + masked[end:]
            count += 1

        return {
            "original_length": len(text),
            "masked_text": masked,
            "masked_count": count,
            "strategy": strategy,
        }

    def get_patterns(self) -> list[dict]:
        """Get all available PII detection patterns."""
        return [
            {
                "pii_type": pii_type,
                "description": config["description"],
                "example": config["example"],
            }
            for pii_type, config in PII_PATTERNS.items()
        ]


# Singleton repository instance
repo = PIIScannerRepository()
