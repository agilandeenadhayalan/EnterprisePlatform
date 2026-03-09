"""
Alerting Rules — PromQL-style alert evaluation, routing, and silencing.

WHY THIS MATTERS:
Alerting is the bridge between observability and incident response.
A well-designed alerting system:
  1. Evaluates conditions against metric values (AlertEvaluator)
  2. Waits for conditions to persist before firing (for_duration)
  3. Routes alerts to the right channels based on severity (RoutingPolicy)
  4. Suppresses known-noisy alerts during maintenance (SilenceRule)

Key concepts:
  - Three-state model: INACTIVE -> PENDING -> FIRING. This prevents
    flapping: a brief spike won't page on-call if it resolves within
    the for_duration window.
  - Routing: CRITICAL goes to PagerDuty, WARNING to Slack, INFO to
    email. Each severity can have multiple channels.
  - Silencing: temporarily suppress alerts during planned maintenance
    so the on-call engineer isn't paged for expected disruptions.
"""

from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels, from most to least urgent.

    CRITICAL — page the on-call engineer immediately (PagerDuty).
    WARNING  — send to team channel for awareness (Slack).
    INFO     — log for later review (email, dashboard).
    """

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertState(Enum):
    """Three-state alert lifecycle.

    INACTIVE — condition is not met. No alert.
    PENDING  — condition is met but hasn't persisted long enough.
               The for_duration window is still counting down.
    FIRING   — condition has persisted for at least for_duration.
               Notifications are sent.
    """

    INACTIVE = "inactive"
    PENDING = "pending"
    FIRING = "firing"


class AlertRule:
    """A declarative alert rule definition.

    Models a Prometheus alerting rule:
        alert: HighErrorRate
        expr: rate(http_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical

    The 'expression' field is a human-readable description of what is
    being checked. The actual evaluation is done by AlertEvaluator using
    the threshold and operator.
    """

    def __init__(
        self,
        name: str,
        expression: str,
        threshold: float,
        operator: str,
        severity: AlertSeverity,
        for_duration_seconds: float = 0.0,
    ):
        self.name = name
        self.expression = expression
        self.threshold = threshold
        self.operator = operator
        self.severity = severity
        self.for_duration_seconds = for_duration_seconds


class AlertEvaluator:
    """Evaluates alert rules against current metric values.

    The evaluation follows Prometheus semantics:
    - Check if the condition (value <operator> threshold) is met.
    - If not met → INACTIVE (reset the timer).
    - If met but duration_active < for_duration → PENDING (keep waiting).
    - If met and duration_active >= for_duration → FIRING (notify!).

    The for_duration mechanism prevents flapping: transient spikes
    won't wake up the on-call engineer at 3 AM.
    """

    def evaluate(self, rule: AlertRule, current_value: float, duration_active: float = 0.0) -> AlertState:
        """Evaluate an alert rule against the current metric value.

        Args:
            rule: The alert rule to evaluate.
            current_value: The current value of the metric.
            duration_active: How long the condition has been continuously
                             met, in seconds.

        Returns:
            AlertState indicating INACTIVE, PENDING, or FIRING.
        """
        condition_met = self._check_condition(current_value, rule.operator, rule.threshold)

        if not condition_met:
            return AlertState.INACTIVE

        if duration_active >= rule.for_duration_seconds:
            return AlertState.FIRING

        return AlertState.PENDING

    def _check_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Check whether the value satisfies the operator/threshold condition.

        Supported operators: gt, lt, gte, lte, eq.
        """
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        elif operator == "eq":
            return value == threshold
        else:
            raise ValueError(f"Unknown operator: '{operator}'")


class RoutingPolicy:
    """Routes firing alerts to notification channels based on severity.

    In production, you want CRITICAL alerts to go to PagerDuty (immediate
    page), WARNING to Slack (team awareness), and INFO to email (async
    review). Each severity can have multiple channels.

    Only FIRING alerts are routed. PENDING and INACTIVE alerts don't
    trigger notifications — this is by design to prevent alert fatigue.
    """

    def __init__(self):
        self._routes: dict[AlertSeverity, list[str]] = {}

    def add_route(self, severity: AlertSeverity, channel: str) -> None:
        """Add a notification channel for a severity level."""
        if severity not in self._routes:
            self._routes[severity] = []
        self._routes[severity].append(channel)

    def get_channels(self, severity: AlertSeverity) -> list:
        """Get all notification channels for a severity level."""
        return self._routes.get(severity, [])

    def route_alert(self, rule: AlertRule, state: AlertState) -> list:
        """Determine which channels to notify for an alert.

        Only FIRING alerts are routed. PENDING and INACTIVE alerts
        return an empty list (no notification).

        Returns:
            List of channel names to notify.
        """
        if state != AlertState.FIRING:
            return []
        return self.get_channels(rule.severity)


class SilenceRule:
    """Temporarily suppress alerts matching specific criteria.

    Used during planned maintenance windows to prevent expected alerts
    from waking on-call engineers. A silence has:
    - matchers: key-value pairs that must all match the alert rule
    - start_time/end_time: the maintenance window

    Example: silence all alerts with name="HighCPU" from 02:00 to 04:00
    during a planned deployment.
    """

    def __init__(self, name: str, matchers: dict, start_time: float, end_time: float):
        self.name = name
        self.matchers = matchers
        self.start_time = start_time
        self.end_time = end_time

    def matches(self, rule: AlertRule) -> bool:
        """Check if this silence rule matches the given alert rule.

        All matchers must match. Matchers are checked against the
        alert rule's attributes (name, severity, expression, etc.).
        """
        for key, value in self.matchers.items():
            rule_value = getattr(rule, key, None)
            # Handle enum comparison
            if hasattr(rule_value, "value"):
                rule_value = rule_value.value
            if rule_value != value:
                return False
        return True

    def is_active(self, current_time: float) -> bool:
        """Check if this silence is currently active.

        A silence is active if current_time falls within
        [start_time, end_time].
        """
        return self.start_time <= current_time <= self.end_time
