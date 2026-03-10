"""
Exercise 5: PII Scanner
========================================
Implement a PII (Personally Identifiable Information) scanner that
uses regex patterns to detect sensitive data in text.

WHY THIS MATTERS:
A mobility platform collects rider names, phone numbers, email addresses,
and payment details. If PII leaks into logs, analytics exports, or ML
training data, you face regulatory penalties and loss of user trust.
Automated PII scanning catches leaks that manual review misses.

Understanding regex-based scanning builds intuition for:
  - Pattern matching across diverse text formats
  - Risk classification and handling priorities
  - Position tracking for targeted masking
  - Structured data vs free-text scanning

YOUR TASK:
Implement the scan(text) method in PIIScanner that:
1. Iterates over all registered patterns
2. For each pattern, uses re.finditer() to find all matches in text
3. Creates a PIIFinding for each match with:
   - name: the pattern name
   - value: the matched text
   - start: match start position
   - end: match end position
4. Returns a list of findings sorted by start position

The add_pattern(name, regex) method is already implemented.
"""

import re
from dataclasses import dataclass


@dataclass
class PIIFinding:
    """A detected PII instance in scanned text."""
    name: str
    value: str
    start: int
    end: int


class PIIScanner:
    """Scan text for PII using registered regex patterns."""

    def __init__(self):
        self._patterns: list = []

    def add_pattern(self, name: str, regex: str) -> None:
        """Register a named regex pattern for PII detection.

        Args:
            name: PII type name (e.g., "ssn", "email")
            regex: regex pattern string
        """
        self._patterns.append({"name": name, "regex": regex})

    def scan(self, text: str) -> list:
        """Scan text for all registered PII patterns.

        For each registered pattern, find all matches in text using
        re.finditer(). Create a PIIFinding for each match.

        Args:
            text: the text to scan

        Returns:
            List of PIIFinding, sorted by start position.

        Algorithm:
            findings = []
            for each pattern in self._patterns:
                for each match from re.finditer(pattern["regex"], text):
                    create PIIFinding(name=pattern["name"],
                                     value=match.group(),
                                     start=match.start(),
                                     end=match.end())
                    append to findings
            sort findings by start position
            return findings
        """
        # YOUR CODE HERE (~10 lines)
        raise NotImplementedError("Implement scan")


# ── Verification ──


def _make_scanner():
    """Helper: create a scanner with standard PII patterns."""
    scanner = PIIScanner()
    scanner.add_pattern("ssn", r"\b\d{3}-\d{2}-\d{4}\b")
    scanner.add_pattern("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    scanner.add_pattern("phone", r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    return scanner


def test_ssn_detection():
    """Scanner detects SSN patterns."""
    scanner = _make_scanner()
    findings = scanner.scan("My SSN is 123-45-6789")
    assert len(findings) >= 1, f"Expected >= 1 finding, got {len(findings)}"
    assert any(f.name == "ssn" for f in findings)
    print("[PASS] test_ssn_detection")


def test_email_detection():
    """Scanner detects email addresses."""
    scanner = _make_scanner()
    findings = scanner.scan("Contact: user@example.com")
    assert any(f.name == "email" for f in findings)
    print("[PASS] test_email_detection")


def test_phone_detection():
    """Scanner detects phone numbers."""
    scanner = _make_scanner()
    findings = scanner.scan("Call 555-123-4567")
    assert any(f.name == "phone" for f in findings)
    print("[PASS] test_phone_detection")


def test_multiple_pii():
    """Multiple PII types detected in one text."""
    scanner = _make_scanner()
    text = "SSN: 123-45-6789, email: test@test.com, phone: 555-987-6543"
    findings = scanner.scan(text)
    assert len(findings) >= 3, f"Expected >= 3 findings, got {len(findings)}"
    print("[PASS] test_multiple_pii")


def test_no_pii():
    """Clean text returns no findings."""
    scanner = _make_scanner()
    findings = scanner.scan("This is a normal sentence with no sensitive data.")
    assert len(findings) == 0, f"Expected 0 findings, got {len(findings)}"
    print("[PASS] test_no_pii")


def test_sorted_by_position():
    """Findings are sorted by start position."""
    scanner = _make_scanner()
    text = "email: a@b.com and SSN: 111-22-3333"
    findings = scanner.scan(text)
    positions = [f.start for f in findings]
    assert positions == sorted(positions), "Findings should be sorted by start position"
    print("[PASS] test_sorted_by_position")


if __name__ == "__main__":
    test_ssn_detection()
    test_email_detection()
    test_phone_detection()
    test_multiple_pii()
    test_no_pii()
    test_sorted_by_position()
    print("\nAll checks passed!")
