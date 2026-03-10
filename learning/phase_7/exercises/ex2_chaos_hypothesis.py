"""
Exercise 2: Chaos Experiment Hypothesis Verification
========================================
Implement verify_hypothesis() to check whether steady-state metrics
stayed within acceptable ranges after a chaos experiment.

WHY THIS MATTERS:
Chaos engineering is the scientific method for distributed systems:
  1. Define steady state: "error rate < 1%, p99 latency < 200ms"
  2. Inject failure: kill a pod, add network latency, exhaust memory
  3. Verify: did the system maintain its steady state?

If the metrics stayed within bounds (including tolerance), the system
is resilient. If any metric violated, you've found a weakness to fix
BEFORE it causes a real outage.

YOUR TASK:
Implement verify_hypothesis(metrics, measurements) that returns a dict
with "passed" (bool) and "violations" (list of violated metric names).
"""

from dataclasses import dataclass


@dataclass
class SteadyStateCheck:
    """A metric with an acceptable range and tolerance.

    Attributes:
        name: metric identifier (e.g., "error_rate", "p99_latency_ms")
        min_val: minimum acceptable value
        max_val: maximum acceptable value
        tolerance: fraction of the range allowed beyond bounds
                   (e.g., 0.1 = 10% beyond min/max is still OK)
    """
    name: str
    min_val: float
    max_val: float
    tolerance: float = 0.0


def verify_hypothesis(
    metrics: list[SteadyStateCheck],
    measurements: dict[str, float],
) -> dict:
    """Verify that all metrics are within their acceptable ranges.

    YOUR TASK:
    For each metric in `metrics`:
      1. Look up its measured value in `measurements`.
      2. If the metric is missing from measurements, it's a violation.
      3. Compute the effective bounds:
         - effective_min = min_val - tolerance * (max_val - min_val)
         - effective_max = max_val + tolerance * (max_val - min_val)
      4. If the measured value is outside [effective_min, effective_max],
         it's a violation.

    Returns:
        dict with:
          - "passed": True if no violations, False otherwise
          - "violations": list of metric names that violated

    Hint: Loop through metrics, check each, collect violation names.
    """
    # YOUR CODE HERE (~12 lines)
    raise NotImplementedError("Implement verify_hypothesis")


# ── Verification ──


def test_all_pass():
    """All metrics within range."""
    metrics = [
        SteadyStateCheck("latency_ms", 0, 200),
        SteadyStateCheck("error_rate", 0, 0.01),
    ]
    result = verify_hypothesis(metrics, {"latency_ms": 100, "error_rate": 0.005})
    assert result["passed"] is True, f"Expected pass, got {result}"
    assert len(result["violations"]) == 0
    print("[PASS] test_all_pass")


def test_single_violation():
    """One metric exceeds range."""
    metrics = [
        SteadyStateCheck("latency_ms", 0, 200),
        SteadyStateCheck("error_rate", 0, 0.01),
    ]
    result = verify_hypothesis(metrics, {"latency_ms": 300, "error_rate": 0.005})
    assert result["passed"] is False
    assert "latency_ms" in result["violations"]
    print("[PASS] test_single_violation")


def test_boundary():
    """Value at exact boundary passes."""
    metrics = [SteadyStateCheck("x", 0, 100)]
    result = verify_hypothesis(metrics, {"x": 100})
    assert result["passed"] is True, f"Boundary value should pass: {result}"
    print("[PASS] test_boundary")


def test_missing_metric():
    """Missing metric is a violation."""
    metrics = [SteadyStateCheck("x", 0, 100)]
    result = verify_hypothesis(metrics, {})
    assert result["passed"] is False
    assert "x" in result["violations"]
    print("[PASS] test_missing_metric")


def test_tolerance_calc():
    """Tolerance extends the acceptable range."""
    metrics = [SteadyStateCheck("x", 0, 100, tolerance=0.1)]
    # Effective max = 100 + 0.1 * 100 = 110
    result = verify_hypothesis(metrics, {"x": 105})
    assert result["passed"] is True, f"Within tolerance should pass: {result}"
    print("[PASS] test_tolerance_calc")


if __name__ == "__main__":
    test_all_pass()
    test_single_violation()
    test_boundary()
    test_missing_metric()
    test_tolerance_calc()
    print("\nAll checks passed!")
