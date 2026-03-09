"""
Circuit Breaker — fault tolerance through fail-fast behavior.

WHY THIS MATTERS:
When a downstream service is failing, continuing to send requests wastes
resources, increases latency, and can cause cascading failures. The circuit
breaker pattern stops sending requests to a failing service ("opens the
circuit"), giving it time to recover. After a timeout, it allows a few
test requests ("half-open") to see if the service has recovered.

Key concepts:
  - CLOSED: normal operation. All requests pass through. Failures are
    counted. When failures reach the threshold, the circuit opens.
  - OPEN: fail-fast mode. All requests are immediately rejected with
    CircuitOpenError. After a timeout, the circuit transitions to
    half-open.
  - HALF_OPEN: trial mode. A limited number of requests are allowed
    through. If they succeed (reaching success_threshold), the circuit
    closes. If any fails, the circuit opens again immediately.

This three-state machine prevents cascading failures while allowing
automatic recovery when the downstream service comes back online.
"""

from enum import Enum
import time


class CircuitBreakerState(Enum):
    """The three states of a circuit breaker.

    CLOSED    — normal operation, requests flow through.
    OPEN      — all requests rejected immediately.
    HALF_OPEN — testing if downstream has recovered.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a request is rejected because the circuit is open.

    This is a signal to the caller that the downstream service is
    known to be unhealthy and the request was not attempted.
    """
    pass


class CircuitBreaker:
    """A circuit breaker implementing the three-state pattern.

    The circuit breaker wraps calls to an external service and monitors
    for failures. When failures exceed the threshold, it stops sending
    requests to protect the system.

    Parameters:
        failure_threshold: number of failures before opening the circuit.
        success_threshold: number of successes in HALF_OPEN before closing.
        timeout_seconds: how long to wait in OPEN before trying HALF_OPEN.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: float = 30.0,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._total_calls = 0
        self._state_transitions: list[tuple[CircuitBreakerState, CircuitBreakerState]] = []

    def _transition(self, new_state: CircuitBreakerState) -> None:
        """Record a state transition."""
        old_state = self._state
        if old_state != new_state:
            self._state_transitions.append((old_state, new_state))
            self._state = new_state

    def call(self, fn: callable):
        """Execute fn through the circuit breaker.

        In CLOSED state: call fn. Track failures. Open if threshold reached.
        In OPEN state: check timeout. If expired, try half-open. Otherwise reject.
        In HALF_OPEN state: call fn. Track successes/failures. Close or re-open.

        Args:
            fn: a callable that takes no arguments and returns a value.

        Returns:
            The return value of fn.

        Raises:
            CircuitOpenError: if the circuit is open and timeout hasn't expired.
            Any exception raised by fn is re-raised after recording the failure.
        """
        self._total_calls += 1

        if self._state == CircuitBreakerState.OPEN:
            # Check if timeout has expired
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.timeout_seconds:
                self._transition(CircuitBreakerState.HALF_OPEN)
                self._success_count = 0
            else:
                raise CircuitOpenError(
                    f"Circuit is open. Retry after {self.timeout_seconds - elapsed:.1f}s"
                )

        # At this point we're either CLOSED or HALF_OPEN
        try:
            result = fn()

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._transition(CircuitBreakerState.CLOSED)
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitBreakerState.CLOSED:
                # Success in closed state resets failure count
                self._failure_count = 0

            return result

        except Exception as e:
            self._last_failure_time = time.time()

            if self._state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open immediately opens
                self._transition(CircuitBreakerState.OPEN)
            elif self._state == CircuitBreakerState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._transition(CircuitBreakerState.OPEN)

            raise

    def get_state(self) -> CircuitBreakerState:
        """Return the current circuit breaker state."""
        return self._state

    def get_metrics(self) -> dict:
        """Return circuit breaker metrics for observability."""
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "state_transitions_count": len(self._state_transitions),
        }
