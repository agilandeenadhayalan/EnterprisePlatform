"""
Exercise 3: Canary Deployment Controller
========================================
Implement a canary deployment controller that gradually shifts traffic
from a stable version to a new "canary" version, with automatic
promotion or rollback based on metrics.

WHY THIS MATTERS:
Canary deployments are the gold standard for safe production deployments.
By routing a small percentage of traffic to the new version first, you
can detect issues (errors, latency spikes) before they affect all users.

The controller you'll build manages the traffic split and uses metrics
to decide whether to promote the canary (make it the new stable) or
roll it back (discard it and revert to stable).

YOUR TASK:
1. Implement deploy(version) — deploy a new canary version
2. Implement shift_traffic(percent) — adjust canary traffic percentage
3. Implement should_promote(metrics) — decide based on error rate and latency
"""


class CanaryController:
    """Manages canary deployments with traffic shifting and metric-based decisions.

    TODO: Implement these methods:

    1. deploy(version) -> None
       Start a canary deployment of the given version.
       Set self.canary_version to the new version.
       Set self.canary_percent to self.initial_percent.
       Raise RuntimeError if a canary is already in progress.

    2. shift_traffic(percent) -> None
       Set the canary traffic percentage to the given value.
       Must be between 0 and 100 (raise ValueError otherwise).
       Raise RuntimeError if no canary is deployed.

    3. should_promote(metrics) -> bool
       Decide if the canary should be promoted based on metrics.
       The metrics dict has keys "error_rate" (float, 0-1) and
       "p99_latency_ms" (float).

       Promote (return True) if:
         - error_rate <= self.max_error_rate AND
         - p99_latency_ms <= self.max_latency_ms

       Otherwise return False (should rollback).

    4. promote() -> None  (PROVIDED)
    5. rollback() -> None  (PROVIDED)
    """

    def __init__(
        self,
        stable_version: str,
        initial_percent: int = 5,
        max_error_rate: float = 0.01,
        max_latency_ms: float = 500.0,
    ):
        self.stable_version = stable_version
        self.canary_version: str | None = None
        self.canary_percent: int = 0
        self.initial_percent = initial_percent
        self.max_error_rate = max_error_rate
        self.max_latency_ms = max_latency_ms

    def deploy(self, version: str) -> None:
        # YOUR CODE HERE (~4 lines)
        raise NotImplementedError("Implement deploy")

    def shift_traffic(self, percent: int) -> None:
        # YOUR CODE HERE (~4 lines)
        raise NotImplementedError("Implement shift_traffic")

    def should_promote(self, metrics: dict) -> bool:
        # YOUR CODE HERE (~3 lines)
        raise NotImplementedError("Implement should_promote")

    # ── PROVIDED — do not modify ──

    def promote(self) -> None:
        """Promote the canary to stable."""
        if self.canary_version is None:
            raise RuntimeError("No canary to promote")
        self.stable_version = self.canary_version
        self.canary_version = None
        self.canary_percent = 0

    def rollback(self) -> None:
        """Rollback the canary, reverting all traffic to stable."""
        self.canary_version = None
        self.canary_percent = 0


# ── Verification ──


def _verify():
    """Run basic checks to verify your implementation."""
    ctrl = CanaryController("1.0.0", initial_percent=5)

    # Test 1: Deploy canary
    ctrl.deploy("2.0.0")
    assert ctrl.canary_version == "2.0.0", "Canary version should be set"
    assert ctrl.canary_percent == 5, f"Expected 5%, got {ctrl.canary_percent}%"
    print("[PASS] deploy: canary deployed at 5%")

    # Test 2: Shift traffic
    ctrl.shift_traffic(25)
    assert ctrl.canary_percent == 25, f"Expected 25%, got {ctrl.canary_percent}%"
    print("[PASS] shift_traffic: canary at 25%")

    # Test 3: Should promote (good metrics)
    good_metrics = {"error_rate": 0.001, "p99_latency_ms": 150.0}
    assert ctrl.should_promote(good_metrics) is True
    print("[PASS] should_promote: good metrics -> True")

    # Test 4: Should NOT promote (bad metrics)
    bad_metrics = {"error_rate": 0.05, "p99_latency_ms": 800.0}
    assert ctrl.should_promote(bad_metrics) is False
    print("[PASS] should_promote: bad metrics -> False")

    # Test 5: Promote
    ctrl.promote()
    assert ctrl.stable_version == "2.0.0"
    assert ctrl.canary_version is None
    print("[PASS] promote: canary became stable")

    # Test 6: Deploy again raises if already deployed
    ctrl.deploy("3.0.0")
    try:
        ctrl.deploy("4.0.0")
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        print("[PASS] deploy: raises if canary already in progress")

    # Test 7: Invalid traffic percentage
    try:
        ctrl.shift_traffic(150)
        assert False, "Should have raised ValueError"
    except ValueError:
        print("[PASS] shift_traffic: rejects invalid percent")

    print("\nAll checks passed!")


if __name__ == "__main__":
    _verify()
