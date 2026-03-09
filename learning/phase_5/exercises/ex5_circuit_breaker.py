"""
Exercise 5: Circuit Breaker — Three-State Fault Tolerance
========================================
Implement a circuit breaker with three states: CLOSED, OPEN, HALF_OPEN.
The circuit breaker wraps calls to an unreliable function and stops sending
requests when failures exceed a threshold.

WHY THIS MATTERS:
When a downstream service is failing, continuing to send requests:
  - Wastes resources (threads, connections, CPU)
  - Increases end-user latency (waiting for timeouts)
  - Can cause cascading failures (your service runs out of threads)

The circuit breaker pattern is used by Netflix Hystrix, Istio, Envoy,
and resilience4j. Understanding the three-state machine is essential for
building reliable distributed systems.

State transitions:
  CLOSED ──(failures >= threshold)──> OPEN
  OPEN   ──(timeout expires)───────> HALF_OPEN
  HALF_OPEN ──(success)────────────> CLOSED
  HALF_OPEN ──(failure)────────────> OPEN

YOUR TASK:
1. Implement call(fn) with three-state logic
2. Track failure_count and handle state transitions
3. Raise CircuitOpenError when circuit is open and timeout hasn't expired
"""

import time


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open."""
    pass


class SimpleCircuitBreaker:
    """
    A circuit breaker with three states.

    TODO: Implement the call(fn) method:

    States:
    - CLOSED: Normal operation. Count failures. If failure_count >= threshold -> OPEN.
    - OPEN: Reject all calls with CircuitOpenError.
             If current_time - last_failure_time >= timeout -> HALF_OPEN.
    - HALF_OPEN: Allow one call through.
                 If it succeeds -> CLOSED (reset failure_count).
                 If it fails -> OPEN (record last_failure_time).

    The method should:
    1. Check the current state.
    2. In CLOSED: call fn(). On success, return result. On exception,
       increment failure_count, record last_failure_time, check threshold.
    3. In OPEN: check if timeout has expired. If yes, transition to
       HALF_OPEN and try the call. If no, raise CircuitOpenError.
    4. In HALF_OPEN: call fn(). On success, transition to CLOSED.
       On exception, transition back to OPEN.
    """

    def __init__(self, failure_threshold: int = 3, timeout_seconds: float = 5.0):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = 0.0

    def call(self, fn):
        """Execute fn through the circuit breaker.

        Returns the result of fn() on success.
        Raises CircuitOpenError if circuit is open.
        Re-raises any exception from fn() after recording the failure.
        """
        # YOUR CODE HERE (~25 lines)
        raise NotImplementedError("Implement call")

    def get_state(self) -> str:
        """Return the current state as a string."""
        return self.state


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    call_count = 0

    def flaky_service():
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            raise ConnectionError("Service unavailable")
        return "success"

    cb = SimpleCircuitBreaker(failure_threshold=3, timeout_seconds=0.1)

    # Test 1: CLOSED state - failures counted
    for i in range(3):
        try:
            cb.call(flaky_service)
        except ConnectionError:
            pass
    assert cb.get_state() == "OPEN", f"Expected OPEN, got {cb.get_state()}"
    print("[PASS] Circuit opens after 3 failures")

    # Test 2: OPEN state rejects calls
    try:
        cb.call(lambda: "should not run")
        assert False, "Should have raised CircuitOpenError"
    except CircuitOpenError:
        print("[PASS] Open circuit rejects calls with CircuitOpenError")

    # Test 3: After timeout, transitions to HALF_OPEN and allows a call
    time.sleep(0.15)
    result = cb.call(flaky_service)  # call_count=4, returns "success"
    assert result == "success", f"Expected 'success', got {result}"
    assert cb.get_state() == "CLOSED", f"Expected CLOSED, got {cb.get_state()}"
    print("[PASS] Circuit closes after successful half-open call")

    # Test 4: Reset works - can handle new failures
    assert cb.failure_count == 0, f"Expected failure_count=0, got {cb.failure_count}"
    print("[PASS] Failure count reset after closing")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
