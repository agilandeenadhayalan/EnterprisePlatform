"""
Hypothesis Testing — define and verify steady-state hypotheses for chaos experiments.

WHY THIS MATTERS:
Chaos engineering is NOT random destruction. It's the scientific method
applied to distributed systems:
  1. Define a hypothesis: "Under normal conditions, p99 latency < 200ms
     and error rate < 0.1%"
  2. Introduce a failure (independent variable)
  3. Measure the steady-state metrics (dependent variables)
  4. Compare: did the system maintain its steady state?

If the hypothesis holds, your system is resilient to that failure.
If it doesn't, you've found a weakness to fix BEFORE it hits production.

Key concepts:
  - Steady-state metrics: the measurable indicators of "normal" behavior.
  - Acceptable range: min/max bounds with tolerance for natural variation.
  - Experiment lifecycle: baseline -> inject -> during -> recover -> after.
  - Violations: which metrics went out of bounds and by how much.
"""

from dataclasses import dataclass, field


@dataclass
class SteadyStateMetric:
    """A single metric that defines part of the steady state.

    Attributes:
        metric_name: identifier (e.g., "p99_latency_ms", "error_rate")
        acceptable_range: (min, max) tuple defining normal bounds
        tolerance_percent: how much beyond the range is tolerated (e.g., 5.0
            means 5% beyond the boundary is still acceptable)
    """
    metric_name: str
    acceptable_range: tuple[float, float]
    tolerance_percent: float = 0.0


class SteadyStateHypothesis:
    """Define and verify a steady-state hypothesis.

    A hypothesis is a collection of metrics with acceptable ranges. The
    system is in steady state if ALL metrics are within their ranges
    (plus tolerance).
    """

    def __init__(self):
        self._metrics: list[SteadyStateMetric] = []

    def add_metric(self, metric: SteadyStateMetric) -> None:
        """Add a metric to the hypothesis definition."""
        self._metrics.append(metric)

    def verify(self, measurements: dict[str, float]) -> bool:
        """Check if all metrics are within acceptable range.

        Args:
            measurements: dict mapping metric_name -> measured_value

        Returns:
            True if ALL metrics are within their acceptable range
            (including tolerance).
        """
        return len(self.get_violations(measurements)) == 0

    def get_violations(self, measurements: dict[str, float]) -> list[dict]:
        """Return which metrics violated their acceptable range.

        Returns:
            List of dicts with "metric", "value", "min", "max",
            "tolerance_percent" for each violation.
        """
        violations = []
        for metric in self._metrics:
            if metric.metric_name not in measurements:
                violations.append({
                    "metric": metric.metric_name,
                    "value": None,
                    "min": metric.acceptable_range[0],
                    "max": metric.acceptable_range[1],
                    "tolerance_percent": metric.tolerance_percent,
                    "reason": "missing",
                })
                continue

            value = measurements[metric.metric_name]
            low, high = metric.acceptable_range

            # Apply tolerance
            tolerance_amount_low = abs(low) * metric.tolerance_percent / 100.0
            tolerance_amount_high = abs(high) * metric.tolerance_percent / 100.0
            effective_low = low - tolerance_amount_low
            effective_high = high + tolerance_amount_high

            if value < effective_low or value > effective_high:
                violations.append({
                    "metric": metric.metric_name,
                    "value": value,
                    "min": low,
                    "max": high,
                    "tolerance_percent": metric.tolerance_percent,
                    "reason": "out_of_range",
                })

        return violations

    @property
    def metrics(self) -> list[SteadyStateMetric]:
        return list(self._metrics)


@dataclass
class ExperimentResult:
    """Result of a chaos experiment.

    Attributes:
        passed: True if the hypothesis held through the experiment
        baseline_measurements: metrics before failure injection
        during_measurements: metrics during failure
        after_measurements: metrics after recovery
        violations: list of metric violations found
        recovery_time_ms: time to return to steady state (0 if never violated)
    """
    passed: bool
    baseline_measurements: dict[str, float]
    during_measurements: dict[str, float]
    after_measurements: dict[str, float]
    violations: list[dict] = field(default_factory=list)
    recovery_time_ms: float = 0.0


class ChaosExperiment:
    """Run a structured chaos experiment with before/during/after measurement.

    Lifecycle:
      1. record_baseline() — capture steady state before chaos
      2. (inject failure externally)
      3. record_during() — capture metrics during failure
      4. (rollback failure externally)
      5. record_after() — capture metrics after recovery
      6. analyze() — compare all phases against the hypothesis
    """

    def __init__(
        self,
        name: str,
        hypothesis: SteadyStateHypothesis,
        failure_config: dict | None = None,
    ):
        self.name = name
        self.hypothesis = hypothesis
        self.failure_config = failure_config or {}
        self._baseline: dict[str, float] = {}
        self._during: dict[str, float] = {}
        self._after: dict[str, float] = {}

    def record_baseline(self, measurements: dict[str, float]) -> None:
        """Capture baseline measurements before chaos injection."""
        self._baseline = dict(measurements)

    def record_during(self, measurements: dict[str, float]) -> None:
        """Capture measurements during the chaos injection."""
        self._during = dict(measurements)

    def record_after(self, measurements: dict[str, float]) -> None:
        """Capture measurements after failure rollback (recovery)."""
        self._after = dict(measurements)

    def analyze(self) -> ExperimentResult:
        """Analyze the experiment by verifying the hypothesis at each phase.

        The experiment passes if:
          - Baseline was in steady state (sanity check)
          - After recovery, the system returned to steady state

        The 'during' phase is expected to have violations — that's the
        whole point of injecting failure. What matters is recovery.
        """
        baseline_violations = self.hypothesis.get_violations(self._baseline)
        during_violations = self.hypothesis.get_violations(self._during)
        after_violations = self.hypothesis.get_violations(self._after)

        # Experiment passes if baseline was healthy and system recovered
        passed = len(baseline_violations) == 0 and len(after_violations) == 0

        # Estimate recovery time based on violation severity
        recovery_time = 0.0
        if during_violations and not after_violations:
            # System recovered — estimate from violation magnitude
            recovery_time = len(during_violations) * 100.0  # simplified model

        all_violations = during_violations + after_violations

        return ExperimentResult(
            passed=passed,
            baseline_measurements=self._baseline,
            during_measurements=self._during,
            after_measurements=self._after,
            violations=all_violations,
            recovery_time_ms=recovery_time,
        )
