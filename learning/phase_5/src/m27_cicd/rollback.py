"""
Rollback Decision Engine — automated rollback based on metrics.

WHY THIS MATTERS:
Automated rollback is the safety net for CI/CD. When a deployment causes
error rates to spike or latency to increase, the rollback engine evaluates
metrics against predefined conditions and triggers a rollback automatically.

Without automated rollback, recovering from a bad deployment depends on
human operators being awake, alert, and able to diagnose the issue quickly.
Automated rollback reduces Mean Time To Recovery (MTTR) from minutes/hours
to seconds.

Common rollback triggers:
  - Error rate > 1% (5xx responses)
  - P99 latency > 500ms
  - CPU usage > 90%
  - Health check failures > 3
"""

from datetime import datetime


class RollbackCondition:
    """A single metric threshold that triggers rollback.

    Supports comparison operators: gt, lt, gte, lte.

    Example:
        RollbackCondition("error_rate", "gt", 0.01)  # >1% errors
        RollbackCondition("p99_latency_ms", "gt", 500)  # >500ms latency

    Attributes:
        metric_name: Name of the metric to check.
        operator: Comparison operator ("gt", "lt", "gte", "lte").
        threshold: The threshold value.
    """

    OPERATORS = {"gt", "lt", "gte", "lte"}

    def __init__(self, metric_name: str, operator: str, threshold: float):
        if operator not in self.OPERATORS:
            raise ValueError(
                f"Invalid operator '{operator}', must be one of {self.OPERATORS}"
            )
        self.metric_name = metric_name
        self.operator = operator
        self.threshold = threshold

    def __repr__(self) -> str:
        return f"RollbackCondition({self.metric_name} {self.operator} {self.threshold})"


class RollbackDecisionEngine:
    """Evaluates metrics against conditions to decide whether to rollback.

    The engine uses OR logic: if ANY required condition is breached,
    rollback is recommended. This is conservative by design — it is
    better to rollback unnecessarily than to let a bad deployment
    continue serving users.

    WHY OR LOGIC:
    In production, different failure modes manifest in different metrics.
    A memory leak shows up in memory usage, not error rate. A database
    connection issue shows up in latency, not CPU. Using OR ensures that
    any single signal is enough to trigger a rollback.
    """

    def __init__(self):
        self._conditions: list[RollbackCondition] = []

    def add_condition(self, condition: RollbackCondition) -> None:
        """Add a rollback condition."""
        self._conditions.append(condition)

    def evaluate_condition(self, condition: RollbackCondition, value: float) -> bool:
        """Evaluate a single condition against a metric value.

        Returns True if the condition is breached (rollback triggered).
        """
        op = condition.operator
        threshold = condition.threshold

        if op == "gt":
            return value > threshold
        elif op == "lt":
            return value < threshold
        elif op == "gte":
            return value >= threshold
        elif op == "lte":
            return value <= threshold
        return False

    def should_rollback(self, metrics: dict[str, float]) -> tuple[bool, list[str]]:
        """Evaluate all conditions against current metrics.

        Returns:
            (should_rollback, list_of_breach_reasons)
        """
        reasons: list[str] = []

        for condition in self._conditions:
            if condition.metric_name in metrics:
                value = metrics[condition.metric_name]
                if self.evaluate_condition(condition, value):
                    reasons.append(
                        f"{condition.metric_name}={value} "
                        f"breaches {condition.operator} {condition.threshold}"
                    )

        return len(reasons) > 0, reasons


class RollbackAction:
    """Record of a rollback that was performed.

    Attributes:
        version_from: The version being rolled back from.
        version_to: The version being rolled back to.
        reason: Why the rollback was triggered.
        timestamp: When the rollback occurred.
        is_automatic: Whether it was triggered automatically.
    """

    def __init__(
        self,
        version_from: str,
        version_to: str,
        reason: str,
        timestamp: datetime | None = None,
        is_automatic: bool = True,
    ):
        self.version_from = version_from
        self.version_to = version_to
        self.reason = reason
        self.timestamp = timestamp or datetime.now()
        self.is_automatic = is_automatic

    def __repr__(self) -> str:
        mode = "auto" if self.is_automatic else "manual"
        return (
            f"RollbackAction({self.version_from} -> {self.version_to}, "
            f"{mode}, reason='{self.reason}')"
        )


class RollbackHistory:
    """Tracks rollback actions for analysis and auditing.

    WHY TRACK ROLLBACKS:
    Rollback history reveals patterns: which services rollback most often,
    what types of changes cause rollbacks, and how quickly the team
    recovers. This data drives process improvements.
    """

    def __init__(self):
        self._actions: list[RollbackAction] = []

    def add(self, action: RollbackAction) -> None:
        """Record a rollback action."""
        self._actions.append(action)

    def get_recent(self, n: int = 10) -> list[RollbackAction]:
        """Get the N most recent rollback actions."""
        return self._actions[-n:]

    def get_stats(self) -> dict[str, int | float]:
        """Compute rollback statistics.

        Returns:
            {
                "total": total rollbacks,
                "automatic": auto-triggered count,
                "manual": manually-triggered count,
            }
        """
        total = len(self._actions)
        automatic = sum(1 for a in self._actions if a.is_automatic)
        manual = total - automatic

        return {
            "total": total,
            "automatic": automatic,
            "manual": manual,
        }
