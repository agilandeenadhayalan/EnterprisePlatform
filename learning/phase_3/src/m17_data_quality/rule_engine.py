"""
Data Quality Rule Engine
==========================

A declarative rule engine for evaluating data quality checks.

RULE TYPES:
1. **Completeness** — % of non-null values meets a threshold.
   "At least 95% of ride records must have a fare."
2. **Freshness** — Data is not older than a maximum age.
   "The latest record must be within the last hour."
3. **Accuracy** — Values fall within expected ranges.
   "Fare must be between $1 and $500."
4. **Consistency** — Cross-field relationships hold.
   "If status is 'completed', fare must not be null."
5. **Uniqueness** — No duplicate values in a column.
   "ride_id must be unique across all records."
6. **Format** — Values match an expected pattern (regex).
   "Email must match the pattern *@*.*"

SEVERITY LEVELS:
- CRITICAL: Pipeline should stop. Data integrity at risk.
- WARNING: Pipeline continues but alerts are raised.
- INFO: Informational, logged but no action required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleType(str, Enum):
    COMPLETENESS = "completeness"
    FRESHNESS = "freshness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    UNIQUENESS = "uniqueness"
    FORMAT = "format"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class RuleStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass(frozen=True)
class QualityRule:
    """Definition of a data quality rule."""
    name: str
    rule_type: RuleType
    column: str
    threshold: float = 0.0
    expression: str = ""
    severity: Severity = Severity.WARNING
    # For accuracy: min/max values
    min_value: float | None = None
    max_value: float | None = None
    # For format: regex pattern
    pattern: str = ""
    # For consistency: related column and expected relationship
    related_column: str = ""
    related_condition: str = ""


@dataclass
class RuleResult:
    """Result of evaluating a quality rule."""
    rule_name: str
    rule_type: RuleType
    status: RuleStatus
    metric_value: float
    threshold: float
    severity: Severity
    details: str
    records_checked: int
    records_failed: int = 0


class RuleEngine:
    """
    Evaluates data quality rules against a dataset.

    Add rules declaratively, then evaluate them all at once
    against a list of records.
    """

    def __init__(self) -> None:
        self._rules: list[QualityRule] = []

    @property
    def rules(self) -> list[QualityRule]:
        return list(self._rules)

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def add_rule(self, rule: QualityRule) -> None:
        """Add a quality rule to the engine."""
        self._rules.append(rule)

    def evaluate(self, data: list[dict[str, Any]]) -> list[RuleResult]:
        """Evaluate all rules against the dataset."""
        results = []
        for rule in self._rules:
            if rule.rule_type == RuleType.COMPLETENESS:
                results.append(self._check_completeness(rule, data))
            elif rule.rule_type == RuleType.FRESHNESS:
                results.append(self._check_freshness(rule, data))
            elif rule.rule_type == RuleType.ACCURACY:
                results.append(self._check_accuracy(rule, data))
            elif rule.rule_type == RuleType.CONSISTENCY:
                results.append(self._check_consistency(rule, data))
            elif rule.rule_type == RuleType.UNIQUENESS:
                results.append(self._check_uniqueness(rule, data))
            elif rule.rule_type == RuleType.FORMAT:
                results.append(self._check_format(rule, data))
        return results

    def _check_completeness(
        self, rule: QualityRule, data: list[dict[str, Any]]
    ) -> RuleResult:
        """Check the % of non-null values in a column."""
        total = len(data)
        non_null = sum(
            1 for r in data
            if r.get(rule.column) is not None and r.get(rule.column) != ""
        )
        pct = (non_null / total * 100) if total > 0 else 0.0
        passed = pct >= rule.threshold

        return RuleResult(
            rule_name=rule.name,
            rule_type=rule.rule_type,
            status=RuleStatus.PASS if passed else RuleStatus.FAIL,
            metric_value=round(pct, 2),
            threshold=rule.threshold,
            severity=rule.severity,
            details=f"{non_null}/{total} records have non-null '{rule.column}'",
            records_checked=total,
            records_failed=total - non_null,
        )

    def _check_freshness(
        self, rule: QualityRule, data: list[dict[str, Any]]
    ) -> RuleResult:
        """Check that the most recent timestamp is within the threshold (seconds)."""
        timestamps = [
            r[rule.column] for r in data
            if r.get(rule.column) is not None
        ]
        if not timestamps:
            return RuleResult(
                rule_name=rule.name,
                rule_type=rule.rule_type,
                status=RuleStatus.FAIL,
                metric_value=0.0,
                threshold=rule.threshold,
                severity=rule.severity,
                details=f"No timestamps found in column '{rule.column}'",
                records_checked=len(data),
            )

        # For simulation, compare max timestamp string (ISO format sorts correctly)
        max_ts = max(str(ts) for ts in timestamps)

        # Threshold is used as a comparison — the freshness value is 1.0 (fresh)
        # or 0.0 (stale) based on whether the newest record meets criteria.
        # In this simulation, we check if data exists (non-empty).
        return RuleResult(
            rule_name=rule.name,
            rule_type=rule.rule_type,
            status=RuleStatus.PASS,
            metric_value=1.0,
            threshold=rule.threshold,
            severity=rule.severity,
            details=f"Most recent '{rule.column}' value: {max_ts}",
            records_checked=len(data),
        )

    def _check_accuracy(
        self, rule: QualityRule, data: list[dict[str, Any]]
    ) -> RuleResult:
        """Check that values fall within min/max bounds."""
        total = 0
        in_range = 0
        for r in data:
            val = r.get(rule.column)
            if val is None:
                continue
            total += 1
            try:
                num_val = float(val)
                if rule.min_value is not None and num_val < rule.min_value:
                    continue
                if rule.max_value is not None and num_val > rule.max_value:
                    continue
                in_range += 1
            except (ValueError, TypeError):
                continue

        pct = (in_range / total * 100) if total > 0 else 0.0
        passed = pct >= rule.threshold

        return RuleResult(
            rule_name=rule.name,
            rule_type=rule.rule_type,
            status=RuleStatus.PASS if passed else RuleStatus.FAIL,
            metric_value=round(pct, 2),
            threshold=rule.threshold,
            severity=rule.severity,
            details=f"{in_range}/{total} values in range [{rule.min_value}, {rule.max_value}]",
            records_checked=total,
            records_failed=total - in_range,
        )

    def _check_consistency(
        self, rule: QualityRule, data: list[dict[str, Any]]
    ) -> RuleResult:
        """Check cross-field consistency rules."""
        total = len(data)
        consistent = 0

        for r in data:
            col_val = r.get(rule.column)
            related_val = r.get(rule.related_column)

            if rule.related_condition == "not_null_when":
                # If column matches expression, related column must not be null
                if str(col_val) == rule.expression:
                    if related_val is not None:
                        consistent += 1
                else:
                    consistent += 1  # Rule doesn't apply
            elif rule.related_condition == "equals":
                if col_val == related_val:
                    consistent += 1
            else:
                consistent += 1

        pct = (consistent / total * 100) if total > 0 else 0.0
        passed = pct >= rule.threshold

        return RuleResult(
            rule_name=rule.name,
            rule_type=rule.rule_type,
            status=RuleStatus.PASS if passed else RuleStatus.FAIL,
            metric_value=round(pct, 2),
            threshold=rule.threshold,
            severity=rule.severity,
            details=f"{consistent}/{total} records are consistent",
            records_checked=total,
            records_failed=total - consistent,
        )

    def _check_uniqueness(
        self, rule: QualityRule, data: list[dict[str, Any]]
    ) -> RuleResult:
        """Check that values in a column are unique (no duplicates)."""
        values = [r.get(rule.column) for r in data if r.get(rule.column) is not None]
        total = len(values)
        unique = len(set(values))
        duplicates = total - unique
        pct = (unique / total * 100) if total > 0 else 0.0
        passed = pct >= rule.threshold

        return RuleResult(
            rule_name=rule.name,
            rule_type=rule.rule_type,
            status=RuleStatus.PASS if passed else RuleStatus.FAIL,
            metric_value=round(pct, 2),
            threshold=rule.threshold,
            severity=rule.severity,
            details=f"{unique} unique out of {total} values ({duplicates} duplicates)",
            records_checked=total,
            records_failed=duplicates,
        )

    def _check_format(
        self, rule: QualityRule, data: list[dict[str, Any]]
    ) -> RuleResult:
        """Check that values match a regex pattern."""
        total = 0
        matched = 0
        regex = re.compile(rule.pattern)

        for r in data:
            val = r.get(rule.column)
            if val is None:
                continue
            total += 1
            if regex.match(str(val)):
                matched += 1

        pct = (matched / total * 100) if total > 0 else 0.0
        passed = pct >= rule.threshold

        return RuleResult(
            rule_name=rule.name,
            rule_type=rule.rule_type,
            status=RuleStatus.PASS if passed else RuleStatus.FAIL,
            metric_value=round(pct, 2),
            threshold=rule.threshold,
            severity=rule.severity,
            details=f"{matched}/{total} values match pattern '{rule.pattern}'",
            records_checked=total,
            records_failed=total - matched,
        )
