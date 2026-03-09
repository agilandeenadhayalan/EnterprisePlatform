"""
Data Quality repository — in-memory rule engine and results store.

Supports rule types: completeness, freshness, accuracy, consistency, uniqueness.
Each rule is evaluated against sample data to produce pass/fail results.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from models import QualityRule, QualityResult, QualitySummary


class QualityRepository:
    """In-memory quality rules and results storage."""

    def __init__(self):
        self._rules: dict[str, QualityRule] = {}
        self._results: dict[str, QualityResult] = {}

    # ── Rule CRUD ──

    def create_rule(
        self,
        dataset_id: str,
        name: str,
        rule_type: str,
        field: str,
        parameters: dict[str, Any],
        description: Optional[str] = None,
        severity: str = "warning",
    ) -> QualityRule:
        """Create a new quality rule."""
        rule_id = str(uuid.uuid4())
        rule = QualityRule(
            id=rule_id,
            dataset_id=dataset_id,
            name=name,
            rule_type=rule_type,
            field=field,
            parameters=parameters,
            description=description,
            severity=severity,
        )
        self._rules[rule_id] = rule
        return rule

    def get_rule(self, rule_id: str) -> Optional[QualityRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(self, dataset_id: Optional[str] = None) -> list[QualityRule]:
        """List rules, optionally filtered by dataset."""
        rules = list(self._rules.values())
        if dataset_id:
            rules = [r for r in rules if r.dataset_id == dataset_id]
        return rules

    def update_rule(self, rule_id: str, **fields) -> Optional[QualityRule]:
        """Update specific fields on a rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(rule, key):
                setattr(rule, key, value)
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    # ── Quality checks ──

    def run_checks(
        self,
        dataset_id: str,
        sample_data: list[dict[str, Any]],
    ) -> list[QualityResult]:
        """Run all rules for a dataset against sample data."""
        rules = self.list_rules(dataset_id=dataset_id)
        results: list[QualityResult] = []

        for rule in rules:
            result = self._evaluate_rule(rule, sample_data)
            self._results[result.id] = result
            results.append(result)

        return results

    def _evaluate_rule(
        self,
        rule: QualityRule,
        sample_data: list[dict[str, Any]],
    ) -> QualityResult:
        """Evaluate a single rule against sample data."""
        result_id = str(uuid.uuid4())

        try:
            if rule.rule_type == "completeness":
                return self._check_completeness(result_id, rule, sample_data)
            elif rule.rule_type == "freshness":
                return self._check_freshness(result_id, rule, sample_data)
            elif rule.rule_type == "accuracy":
                return self._check_accuracy(result_id, rule, sample_data)
            elif rule.rule_type == "consistency":
                return self._check_consistency(result_id, rule, sample_data)
            elif rule.rule_type == "uniqueness":
                return self._check_uniqueness(result_id, rule, sample_data)
            else:
                return QualityResult(
                    id=result_id,
                    rule_id=rule.id,
                    dataset_id=rule.dataset_id,
                    status="error",
                    message=f"Unknown rule type: {rule.rule_type}",
                )
        except Exception as e:
            return QualityResult(
                id=result_id,
                rule_id=rule.id,
                dataset_id=rule.dataset_id,
                status="error",
                message=str(e),
            )

    def _check_completeness(
        self,
        result_id: str,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> QualityResult:
        """Check what percentage of records have non-null values for the field."""
        if not data:
            return QualityResult(
                id=result_id, rule_id=rule.id, dataset_id=rule.dataset_id,
                status="passed", message="No data to check",
                actual_value=1.0, expected_value=rule.parameters.get("min_completeness", 0.95),
            )

        non_null = sum(1 for row in data if row.get(rule.field) is not None)
        completeness = non_null / len(data)
        threshold = rule.parameters.get("min_completeness", 0.95)

        return QualityResult(
            id=result_id,
            rule_id=rule.id,
            dataset_id=rule.dataset_id,
            status="passed" if completeness >= threshold else "failed",
            message=f"Completeness: {completeness:.2%} (threshold: {threshold:.2%})",
            actual_value=round(completeness, 4),
            expected_value=threshold,
        )

    def _check_freshness(
        self,
        result_id: str,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> QualityResult:
        """Check if data is within the freshness window (max age in hours)."""
        max_age_hours = rule.parameters.get("max_age_hours", 24)

        if not data:
            return QualityResult(
                id=result_id, rule_id=rule.id, dataset_id=rule.dataset_id,
                status="passed", message="No data to check",
            )

        # Find the most recent timestamp
        timestamps = []
        for row in data:
            val = row.get(rule.field)
            if val:
                try:
                    if isinstance(val, str):
                        ts = datetime.fromisoformat(val.replace("Z", "+00:00").replace("+00:00", ""))
                    else:
                        ts = val
                    timestamps.append(ts)
                except (ValueError, TypeError):
                    pass

        if not timestamps:
            return QualityResult(
                id=result_id, rule_id=rule.id, dataset_id=rule.dataset_id,
                status="error", message=f"No valid timestamps found in field '{rule.field}'",
            )

        newest = max(timestamps)
        age_hours = (datetime.utcnow() - newest).total_seconds() / 3600
        is_fresh = age_hours <= max_age_hours

        return QualityResult(
            id=result_id,
            rule_id=rule.id,
            dataset_id=rule.dataset_id,
            status="passed" if is_fresh else "failed",
            message=f"Data age: {age_hours:.1f}h (max: {max_age_hours}h)",
            actual_value=round(age_hours, 2),
            expected_value=max_age_hours,
        )

    def _check_accuracy(
        self,
        result_id: str,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> QualityResult:
        """Check if numeric values fall within min/max range."""
        min_val = rule.parameters.get("min_value")
        max_val = rule.parameters.get("max_value")

        if not data:
            return QualityResult(
                id=result_id, rule_id=rule.id, dataset_id=rule.dataset_id,
                status="passed", message="No data to check",
            )

        out_of_range = 0
        total = 0
        for row in data:
            val = row.get(rule.field)
            if val is not None:
                total += 1
                try:
                    num_val = float(val)
                    if min_val is not None and num_val < min_val:
                        out_of_range += 1
                    elif max_val is not None and num_val > max_val:
                        out_of_range += 1
                except (ValueError, TypeError):
                    out_of_range += 1

        accuracy = (total - out_of_range) / total if total > 0 else 1.0
        threshold = rule.parameters.get("min_accuracy", 0.95)

        return QualityResult(
            id=result_id,
            rule_id=rule.id,
            dataset_id=rule.dataset_id,
            status="passed" if accuracy >= threshold else "failed",
            message=f"Accuracy: {accuracy:.2%} ({out_of_range} out of range)",
            actual_value=round(accuracy, 4),
            expected_value=threshold,
        )

    def _check_consistency(
        self,
        result_id: str,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> QualityResult:
        """Check cross-field consistency (e.g., end_time > start_time)."""
        related_field = rule.parameters.get("related_field")
        relation = rule.parameters.get("relation", "greater_than")

        if not data or not related_field:
            return QualityResult(
                id=result_id, rule_id=rule.id, dataset_id=rule.dataset_id,
                status="passed" if not data else "error",
                message="No data to check" if not data else "Missing 'related_field' parameter",
            )

        inconsistent = 0
        total = 0
        for row in data:
            val_a = row.get(rule.field)
            val_b = row.get(related_field)
            if val_a is not None and val_b is not None:
                total += 1
                if relation == "greater_than" and not (val_a > val_b):
                    inconsistent += 1
                elif relation == "less_than" and not (val_a < val_b):
                    inconsistent += 1
                elif relation == "equals" and val_a != val_b:
                    inconsistent += 1

        consistency = (total - inconsistent) / total if total > 0 else 1.0

        return QualityResult(
            id=result_id,
            rule_id=rule.id,
            dataset_id=rule.dataset_id,
            status="passed" if inconsistent == 0 else "failed",
            message=f"Consistency: {consistency:.2%} ({inconsistent} inconsistent)",
            actual_value=round(consistency, 4),
            expected_value=1.0,
        )

    def _check_uniqueness(
        self,
        result_id: str,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> QualityResult:
        """Check if values in a field are unique (no duplicates)."""
        if not data:
            return QualityResult(
                id=result_id, rule_id=rule.id, dataset_id=rule.dataset_id,
                status="passed", message="No data to check",
                actual_value=1.0, expected_value=1.0,
            )

        values = [row.get(rule.field) for row in data if row.get(rule.field) is not None]
        unique_count = len(set(values))
        total_count = len(values)
        uniqueness = unique_count / total_count if total_count > 0 else 1.0
        threshold = rule.parameters.get("min_uniqueness", 1.0)

        return QualityResult(
            id=result_id,
            rule_id=rule.id,
            dataset_id=rule.dataset_id,
            status="passed" if uniqueness >= threshold else "failed",
            message=f"Uniqueness: {uniqueness:.2%} ({total_count - unique_count} duplicates)",
            actual_value=round(uniqueness, 4),
            expected_value=threshold,
        )

    # ── Results queries ──

    def list_results(
        self,
        rule_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[QualityResult]:
        """List quality results with optional filters."""
        results = list(self._results.values())
        if rule_id:
            results = [r for r in results if r.rule_id == rule_id]
        if status:
            results = [r for r in results if r.status == status]
        return results

    def get_summary(self, dataset_id: str) -> QualitySummary:
        """Get quality summary for a dataset."""
        results = [r for r in self._results.values() if r.dataset_id == dataset_id]
        rules = self.list_rules(dataset_id=dataset_id)
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        errors = sum(1 for r in results if r.status == "error")
        total = len(results)
        score = passed / total if total > 0 else 0.0

        return QualitySummary(
            dataset_id=dataset_id,
            total_rules=len(rules),
            passed=passed,
            failed=failed,
            errors=errors,
            score=round(score, 4),
        )


# Singleton repository instance
repo = QualityRepository()
