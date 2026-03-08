"""
Exercise 7: Advanced Circuit Breaker with Metrics
===================================================

Extend the basic circuit breaker with:
- Failure rate threshold (percentage, not count)
- Sliding window of recent results
- Metrics tracking (total calls, success rate, state transitions)

This is closer to how Resilience4j and Hystrix actually work.
"""

from collections import deque
from dataclasses import dataclass, field
from learning.phase_1.src.m01_api_gateway.gateway import CircuitBreaker, CircuitState


class MetricsCircuitBreaker:
    """
    Circuit breaker with percentage-based failure threshold and metrics.

    Configuration:
    - failure_rate_threshold: Open circuit if failure rate exceeds this (0.0-1.0)
    - window_size: Number of recent calls to consider
    - min_calls: Minimum calls before evaluating failure rate

    Example:
        cb = MetricsCircuitBreaker(failure_rate_threshold=0.5, window_size=10)
        # Opens when 50%+ of last 10 calls failed
    """

    def __init__(self, failure_rate_threshold: float = 0.5,
                 window_size: int = 10, min_calls: int = 5,
                 recovery_timeout: float = 30.0) -> None:
        self.failure_rate_threshold = failure_rate_threshold
        self.window_size = window_size
        self.min_calls = min_calls
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.results: deque[bool] = deque(maxlen=window_size)  # True=success, False=failure
        self.state_transitions: list[tuple[str, str]] = []
        self.total_calls = 0

    def record_result(self, success: bool) -> None:
        """
        Record a call result and evaluate circuit state.

        Steps:
        1. Add result to sliding window
        2. Increment total_calls
        3. If we have >= min_calls results:
           a. Calculate failure rate = failures / total in window
           b. If failure_rate > threshold → transition to OPEN
        4. If in HALF_OPEN: success → CLOSED, failure → OPEN
        5. Track state transitions
        """
        # TODO: Implement result recording and state evaluation (~15 lines)
        raise NotImplementedError("Implement metrics-based circuit breaker")

    @property
    def failure_rate(self) -> float:
        """Current failure rate in the sliding window."""
        if not self.results:
            return 0.0
        failures = sum(1 for r in self.results if not r)
        return failures / len(self.results)

    @property
    def metrics(self) -> dict:
        """Return circuit breaker metrics."""
        return {
            "state": self.state.value,
            "total_calls": self.total_calls,
            "failure_rate": f"{self.failure_rate:.1%}",
            "window_size": len(self.results),
            "transitions": len(self.state_transitions),
        }


# ── Tests ──


def test_stays_closed_under_threshold():
    cb = MetricsCircuitBreaker(failure_rate_threshold=0.5, window_size=10, min_calls=5)
    for _ in range(8):
        cb.record_result(True)
    for _ in range(2):
        cb.record_result(False)
    # 20% failure rate < 50% threshold
    assert cb.state == CircuitState.CLOSED


def test_opens_over_threshold():
    cb = MetricsCircuitBreaker(failure_rate_threshold=0.5, window_size=10, min_calls=5)
    for _ in range(3):
        cb.record_result(True)
    for _ in range(7):
        cb.record_result(False)
    # 70% failure rate > 50% threshold
    assert cb.state == CircuitState.OPEN


def test_min_calls_respected():
    cb = MetricsCircuitBreaker(failure_rate_threshold=0.5, window_size=10, min_calls=5)
    for _ in range(4):
        cb.record_result(False)
    # Only 4 calls < min_calls=5, should stay closed
    assert cb.state == CircuitState.CLOSED
