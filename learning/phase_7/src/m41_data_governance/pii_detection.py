"""
PII detection and masking — finding and protecting personal data.

WHY THIS MATTERS:
A mobility platform collects rider names, phone numbers, email addresses,
payment details, and precise location histories. Accidental exposure of
PII in logs, analytics exports, or ML training data is both a regulatory
violation (GDPR, CCPA) and a trust-destroying event. Automated PII
scanning catches leaks that manual review misses.

Key concepts:
  - Pattern matching: regex-based detection for structured PII formats
  - Risk classification: SSN/credit card = critical, email = medium
  - Masking strategies: redaction, partial masking, hashing
  - Structured data scanning: checking each field in a record
"""

import re
import hashlib
from dataclasses import dataclass, field
from enum import Enum


class PIIType(Enum):
    """Categories of personally identifiable information.

    Each type has different regulatory implications and risk levels.
    """

    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"


@dataclass
class PIIPattern:
    """A regex pattern for detecting a specific PII type.

    Each pattern has a risk level that determines handling priority:
    - low: IP addresses, dates
    - medium: email, phone
    - high: SSN, passport
    - critical: credit card, financial data
    """

    pii_type: PIIType
    pattern: str  # regex pattern string
    description: str
    risk_level: str  # "low", "medium", "high", "critical"


@dataclass
class PIIFinding:
    """A detected PII instance in scanned text.

    Records the type, matched value, position in text, risk level,
    and a pre-computed masked version for easy remediation.
    """

    pii_type: PIIType
    value: str
    start_pos: int
    end_pos: int
    risk_level: str
    masked_value: str


class PIIScanner:
    """Scan text and structured data for PII using regex patterns.

    Initialized with built-in patterns for common PII types.
    Custom patterns can be added for domain-specific detection.
    """

    def __init__(self):
        """Initialize with built-in patterns for SSN, email, phone, credit card, IP."""
        self._patterns: list = [
            PIIPattern(
                pii_type=PIIType.SSN,
                pattern=r"\b\d{3}-\d{2}-\d{4}\b",
                description="Social Security Number",
                risk_level="high",
            ),
            PIIPattern(
                pii_type=PIIType.EMAIL,
                pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                description="Email address",
                risk_level="medium",
            ),
            PIIPattern(
                pii_type=PIIType.PHONE,
                pattern=r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                description="Phone number",
                risk_level="medium",
            ),
            PIIPattern(
                pii_type=PIIType.CREDIT_CARD,
                pattern=r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                description="Credit card number",
                risk_level="critical",
            ),
            PIIPattern(
                pii_type=PIIType.IP_ADDRESS,
                pattern=r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
                description="IP address",
                risk_level="low",
            ),
        ]

    def add_pattern(self, pattern: PIIPattern) -> None:
        """Add a custom PII detection pattern."""
        self._patterns.append(pattern)

    def scan(self, text: str) -> list:
        """Scan text for PII matches using all registered patterns.

        Returns list of PIIFinding, one per match. Matches are sorted
        by start position.
        """
        findings = []
        for pat in self._patterns:
            for match in re.finditer(pat.pattern, text):
                masker = PIIMasker()
                findings.append(PIIFinding(
                    pii_type=pat.pii_type,
                    value=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    risk_level=pat.risk_level,
                    masked_value=masker.mask(match.group(), "redact"),
                ))
        findings.sort(key=lambda f: f.start_pos)
        return findings

    def scan_structured(self, data: dict) -> dict:
        """Scan a dictionary's values for PII.

        Returns dict mapping field_name -> list of PIIFinding.
        Only includes fields where PII was found.
        """
        results = {}
        for field_name, value in data.items():
            if isinstance(value, str):
                findings = self.scan(value)
                if findings:
                    results[field_name] = findings
        return results


class PIIMasker:
    """Mask PII values using various strategies.

    Supports three masking strategies:
    - redact: replace entirely with "[REDACTED]"
    - partial: show last 4 characters, mask the rest
    - hash: SHA256 hash, first 8 characters
    """

    def mask(self, value: str, strategy: str = "redact") -> str:
        """Mask a PII value using the specified strategy.

        Args:
            value: the raw PII value
            strategy: "redact", "partial", or "hash"

        Returns:
            Masked version of the value.
        """
        if strategy == "redact":
            return "[REDACTED]"
        elif strategy == "partial":
            if len(value) <= 4:
                return "***" + value
            return "***" + value[-4:]
        elif strategy == "hash":
            h = hashlib.sha256(value.encode()).hexdigest()
            return h[:8]
        else:
            return "[REDACTED]"

    def mask_text(self, text: str, findings: list) -> str:
        """Replace all PII findings in text with masked versions.

        Processes findings from right to left to preserve positions.
        """
        # Sort by start_pos descending to replace from end to start
        sorted_findings = sorted(findings, key=lambda f: f.start_pos, reverse=True)
        result = text
        for finding in sorted_findings:
            result = result[:finding.start_pos] + finding.masked_value + result[finding.end_pos:]
        return result
