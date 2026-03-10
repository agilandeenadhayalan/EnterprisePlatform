"""
Exercise 4: Little's Law and Queue Analysis
========================================
Implement the core queuing formulas for a single-server system.

WHY THIS MATTERS:
Every request in a distributed system passes through queues: network
buffers, thread pools, connection pools, message queues. Little's Law
(L = lambda * W) is the most fundamental result in queuing theory and
holds for ANY stable system. Understanding utilization tells you when
your system is about to hit the hockey-stick latency curve.

Key formulas for M/M/1 queue:
  - Utilization: rho = lambda / mu
  - Avg items in system: L = rho / (1 - rho)
  - Avg time in system: W = 1 / (mu - lambda)
  - Little's Law: L = lambda * W

YOUR TASK:
Implement three methods on QueueSystem:
  1. utilization() -> rho = arrival_rate / service_rate
  2. avg_items_in_system() -> L = rho / (1 - rho), inf if rho >= 1
  3. avg_time_in_system() -> W = 1 / (mu - lambda), inf if lambda >= mu
"""


class QueueSystem:
    """A single-server M/M/1 queuing system.

    Attributes:
        arrival_rate: lambda — average requests arriving per second
        service_rate: mu — average requests the server can handle per second
    """

    def __init__(self, arrival_rate: float, service_rate: float):
        self.arrival_rate = arrival_rate  # lambda
        self.service_rate = service_rate  # mu

    def utilization(self) -> float:
        """Server utilization rho = lambda / mu.

        YOUR TASK: Return lambda / mu. Handle mu=0 by returning inf.
        """
        # YOUR CODE HERE (~2 lines)
        raise NotImplementedError("Implement utilization")

    def avg_items_in_system(self) -> float:
        """Average items in the system L = rho / (1 - rho).

        YOUR TASK: Compute rho from utilization(). If rho >= 1, return inf.
        Otherwise return rho / (1 - rho).
        """
        # YOUR CODE HERE (~4 lines)
        raise NotImplementedError("Implement avg_items_in_system")

    def avg_time_in_system(self) -> float:
        """Average time in system W = 1 / (mu - lambda).

        YOUR TASK: If lambda >= mu, return inf. Otherwise return 1 / (mu - lambda).
        """
        # YOUR CODE HERE (~3 lines)
        raise NotImplementedError("Implement avg_time_in_system")


# ── Verification ──


def test_low_utilization():
    """Low utilization: short waits."""
    q = QueueSystem(arrival_rate=20, service_rate=100)
    assert abs(q.utilization() - 0.2) < 0.01, f"Expected ~0.2, got {q.utilization()}"
    assert q.avg_items_in_system() < 1.0, "Should have < 1 item in system"
    print("[PASS] test_low_utilization")


def test_high_utilization():
    """High utilization: long waits."""
    q = QueueSystem(arrival_rate=90, service_rate=100)
    assert abs(q.utilization() - 0.9) < 0.01
    assert q.avg_items_in_system() > 5.0, "Should have many items at high util"
    print("[PASS] test_high_utilization")


def test_boundary():
    """At rho=1, system is unstable (infinite queue)."""
    q = QueueSystem(arrival_rate=100, service_rate=100)
    assert q.avg_items_in_system() == float("inf")
    assert q.avg_time_in_system() == float("inf")
    print("[PASS] test_boundary")


def test_littles_law_relationship():
    """Verify L = lambda * W."""
    q = QueueSystem(arrival_rate=60, service_rate=100)
    L = q.avg_items_in_system()
    W = q.avg_time_in_system()
    expected_L = q.arrival_rate * W
    assert abs(L - expected_L) < 0.001, f"L={L} != lambda*W={expected_L}"
    print("[PASS] test_littles_law_relationship")


def test_overloaded():
    """Overloaded system (lambda > mu) returns inf."""
    q = QueueSystem(arrival_rate=150, service_rate=100)
    assert q.utilization() > 1.0
    assert q.avg_items_in_system() == float("inf")
    assert q.avg_time_in_system() == float("inf")
    print("[PASS] test_overloaded")


if __name__ == "__main__":
    test_low_utilization()
    test_high_utilization()
    test_boundary()
    test_littles_law_relationship()
    test_overloaded()
    print("\nAll checks passed!")
