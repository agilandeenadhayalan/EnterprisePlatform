"""
Exercise 4: Quality Rule Evaluator
=====================================

The data quality module demonstrated a rule engine for checking
data quality. Now implement your own rule evaluator.

TASK:
Build a simple quality rule evaluator that checks:
1. Completeness — % of non-null values exceeds a threshold.
2. Accuracy — % of values in an expected range exceeds a threshold.
3. Freshness — The most recent timestamp is within a max age.

Each rule returns pass/fail with the computed metric value.

WHY quality rules:
- Catch data issues before they reach dashboards.
- Automate quality checks that humans would miss.
- Establish trust in your data pipeline.
"""


class QualityRuleEvaluator:
    """
    TODO: Implement a quality rule evaluator that supports:
    1. Completeness check (% non-null > threshold)
    2. Accuracy check (% values in range > threshold)
    3. Freshness check (newest timestamp within max_age_seconds)
    """

    def __init__(self) -> None:
        """Initialize the rule list."""
        # TODO: Initialize (~1 line)
        raise NotImplementedError("Initialize rule evaluator")

    def add_completeness_rule(
        self, name: str, column: str, threshold_pct: float
    ) -> None:
        """
        Add a completeness rule.

        The rule passes if the percentage of non-null values
        in the column >= threshold_pct.
        """
        # TODO: Store the rule (~3 lines)
        raise NotImplementedError("Add completeness rule")

    def add_accuracy_rule(
        self, name: str, column: str, min_value: float, max_value: float, threshold_pct: float
    ) -> None:
        """
        Add an accuracy rule.

        The rule passes if the percentage of values within
        [min_value, max_value] >= threshold_pct.
        """
        # TODO: Store the rule (~3 lines)
        raise NotImplementedError("Add accuracy rule")

    def add_freshness_rule(
        self, name: str, column: str, max_age_seconds: float
    ) -> None:
        """
        Add a freshness rule.

        The rule passes if the most recent value in the column
        is within max_age_seconds of the current time.

        Hint: Use datetime.fromisoformat() and datetime.now().
        """
        # TODO: Store the rule (~3 lines)
        raise NotImplementedError("Add freshness rule")

    def evaluate(self, data: list[dict]) -> list[dict]:
        """
        Evaluate all rules against the dataset.

        Returns a list of results, each with:
        - name: rule name
        - rule_type: "completeness", "accuracy", or "freshness"
        - passed: True/False
        - metric_value: the computed metric
        - threshold: the threshold used
        """
        # TODO: Implement (~30 lines for all 3 rule types)
        raise NotImplementedError("Evaluate rules")


# ── Verification ──


def test_completeness_pass():
    ev = QualityRuleEvaluator()
    ev.add_completeness_rule("fare_complete", "fare", 60.0)
    data = [{"fare": 10}, {"fare": 20}, {"fare": None}]
    results = ev.evaluate(data)
    assert results[0]["passed"] is True
    assert abs(results[0]["metric_value"] - 66.67) < 1


def test_completeness_fail():
    ev = QualityRuleEvaluator()
    ev.add_completeness_rule("fare_complete", "fare", 90.0)
    data = [{"fare": None}, {"fare": None}, {"fare": 10}]
    results = ev.evaluate(data)
    assert results[0]["passed"] is False


def test_accuracy():
    ev = QualityRuleEvaluator()
    ev.add_accuracy_rule("fare_range", "fare", 0, 100, 100.0)
    data = [{"fare": 25}, {"fare": 500}]
    results = ev.evaluate(data)
    assert results[0]["passed"] is False
    assert results[0]["metric_value"] == 50.0


def test_multiple_rules():
    ev = QualityRuleEvaluator()
    ev.add_completeness_rule("r1", "fare", 50.0)
    ev.add_accuracy_rule("r2", "fare", 0, 100, 100.0)
    data = [{"fare": 25}, {"fare": 50}]
    results = ev.evaluate(data)
    assert len(results) == 2


if __name__ == "__main__":
    try:
        test_completeness_pass()
        test_completeness_fail()
        test_accuracy()
        test_multiple_rules()
        print("All tests passed!")
    except NotImplementedError as e:
        print(f"Not yet implemented: {e}")
    except AssertionError as e:
        print(f"Test failed: {e}")
