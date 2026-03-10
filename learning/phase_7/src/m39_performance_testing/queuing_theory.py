"""
Queuing Theory — mathematical models for system capacity and latency.

WHY THIS MATTERS:
Every request in a distributed system goes through queues: network buffers,
thread pools, database connection pools, message queues. Queuing theory
gives you the math to predict how these queues behave under load.

The most important insight: latency increases EXPONENTIALLY as utilization
approaches 100%. At 50% utilization, wait time equals service time. At 90%,
wait time is 9x the service time. At 99%, it's 99x. This is why capacity
planning targets 60-70% utilization — you need headroom for spikes.

Key formulas:
  - Little's Law: L = lambda * W (items in system = arrival rate * time)
  - M/M/1 queue: single server with Poisson arrivals and exponential service
  - M/M/c queue: multi-server extension
  - Utilization: rho = lambda / (c * mu), where c = number of servers
"""

import math
from dataclasses import dataclass


class LittlesLaw:
    """Little's Law: L = lambda * W.

    The most fundamental result in queuing theory. Holds for ANY
    stable system regardless of arrival distribution, service
    distribution, or number of servers.

    L = average items in the system
    lambda = average arrival rate
    W = average time in the system
    """

    @staticmethod
    def items_in_system(arrival_rate: float, avg_time: float) -> float:
        """L = lambda * W"""
        return arrival_rate * avg_time

    @staticmethod
    def avg_time(arrival_rate: float, items_in_system: float) -> float:
        """W = L / lambda"""
        if arrival_rate == 0:
            return 0.0
        return items_in_system / arrival_rate

    @staticmethod
    def arrival_rate(items_in_system: float, avg_time: float) -> float:
        """lambda = L / W"""
        if avg_time == 0:
            return 0.0
        return items_in_system / avg_time


class MM1Queue:
    """M/M/1 queue: single server, Poisson arrivals, exponential service.

    The simplest queuing model but remarkably useful for capacity planning.
    Demonstrates the critical insight that latency grows exponentially
    as utilization approaches 1.0.

    Parameters:
        lambda (arrival_rate): average requests per second arriving
        mu (service_rate): average requests per second the server can handle

    Stability condition: lambda < mu (utilization < 1.0)
    """

    def __init__(self, arrival_rate: float, service_rate: float):
        self.arrival_rate = arrival_rate  # lambda
        self.service_rate = service_rate  # mu

    def utilization(self) -> float:
        """rho = lambda / mu. Must be < 1 for stability."""
        if self.service_rate == 0:
            return float("inf")
        return self.arrival_rate / self.service_rate

    def avg_queue_length(self) -> float:
        """Lq = rho^2 / (1 - rho). Average items waiting in queue."""
        rho = self.utilization()
        if rho >= 1.0:
            return float("inf")
        return rho ** 2 / (1 - rho)

    def avg_wait_time(self) -> float:
        """Wq = rho / (mu - lambda). Average time waiting in queue."""
        if self.arrival_rate >= self.service_rate:
            return float("inf")
        rho = self.utilization()
        return rho / (self.service_rate - self.arrival_rate)

    def avg_system_time(self) -> float:
        """W = 1 / (mu - lambda). Average total time in system."""
        if self.arrival_rate >= self.service_rate:
            return float("inf")
        return 1.0 / (self.service_rate - self.arrival_rate)

    def probability_empty(self) -> float:
        """P0 = 1 - rho. Probability the system is idle."""
        rho = self.utilization()
        if rho >= 1.0:
            return 0.0
        return 1.0 - rho

    def avg_items_in_system(self) -> float:
        """L = rho / (1 - rho). Average items in the system (queue + service)."""
        rho = self.utilization()
        if rho >= 1.0:
            return float("inf")
        return rho / (1 - rho)


class MMcQueue:
    """M/M/c queue: c servers, Poisson arrivals, exponential service.

    Extends M/M/1 to multiple identical servers. Requests go to any
    available server. If all servers are busy, requests queue.

    The key insight: adding servers provides diminishing returns.
    Going from 1 to 2 servers halves the wait time, but going from
    10 to 11 barely helps.
    """

    def __init__(self, arrival_rate: float, service_rate: float, num_servers: int):
        self.arrival_rate = arrival_rate  # lambda
        self.service_rate = service_rate  # mu per server
        self.num_servers = num_servers    # c

    def utilization(self) -> float:
        """rho = lambda / (c * mu). Per-server utilization."""
        if self.num_servers * self.service_rate == 0:
            return float("inf")
        return self.arrival_rate / (self.num_servers * self.service_rate)

    def _erlang_c(self) -> float:
        """Erlang C formula: probability all servers are busy.

        C(c, A) where A = lambda/mu (offered load), c = num_servers.
        """
        A = self.arrival_rate / self.service_rate  # offered load
        c = self.num_servers
        rho = self.utilization()

        if rho >= 1.0:
            return 1.0

        # Compute A^c / c!
        numerator = (A ** c) / math.factorial(c) * (1 / (1 - rho))

        # Compute sum(A^k / k!) for k=0..c-1
        denominator = sum(A ** k / math.factorial(k) for k in range(c))
        denominator += numerator

        return numerator / denominator

    def avg_wait_time(self) -> float:
        """Average time waiting in queue (Wq)."""
        rho = self.utilization()
        if rho >= 1.0:
            return float("inf")

        ec = self._erlang_c()
        return ec / (self.num_servers * self.service_rate * (1 - rho))

    def avg_system_time(self) -> float:
        """Average total time in system (W = Wq + 1/mu)."""
        return self.avg_wait_time() + 1.0 / self.service_rate

    def avg_queue_length(self) -> float:
        """Average items waiting in queue (Lq = lambda * Wq)."""
        return self.arrival_rate * self.avg_wait_time()


def utilization_vs_latency(
    service_rate: float,
    utilization_points: list[float],
) -> list[dict]:
    """Compute wait time at each utilization point — the hockey stick curve.

    # YOUR CODE HERE
    # The key insight: wait time grows as rho / (mu * (1 - rho)).
    # At low utilization (rho=0.1), wait is tiny.
    # At high utilization (rho=0.9), wait is 9x service time.
    # At rho=0.99, wait is 99x service time.
    # This is WHY you never run systems at 100% — the latency explodes.

    Args:
        service_rate: mu — requests the server can process per second
        utilization_points: list of utilization values (0.0 to <1.0)

    Returns:
        List of dicts with "utilization", "wait_time", "system_time",
        "wait_multiplier" (wait_time / service_time).
    """
    service_time = 1.0 / service_rate if service_rate > 0 else 0.0
    results = []

    for rho in utilization_points:
        if rho >= 1.0:
            results.append({
                "utilization": rho,
                "wait_time": float("inf"),
                "system_time": float("inf"),
                "wait_multiplier": float("inf"),
            })
            continue

        # Arrival rate for this utilization: rho = lambda / mu => lambda = rho * mu
        arrival_rate = rho * service_rate
        wait_time = rho / (service_rate - arrival_rate) if service_rate > arrival_rate else float("inf")
        system_time = wait_time + service_time

        results.append({
            "utilization": rho,
            "wait_time": round(wait_time, 6),
            "system_time": round(system_time, 6),
            "wait_multiplier": round(wait_time / service_time, 2) if service_time > 0 else 0.0,
        })

    return results


class CapacityCalculator:
    """Calculate capacity limits from queuing theory parameters."""

    @staticmethod
    def max_throughput(service_rate: float, target_latency_ms: float) -> float:
        """Maximum arrival rate to stay under target system latency.

        From W = 1 / (mu - lambda):
          lambda = mu - 1/W

        where W is in seconds.
        """
        target_seconds = target_latency_ms / 1000.0
        if target_seconds <= 0:
            return 0.0

        max_lambda = service_rate - (1.0 / target_seconds)
        return max(0.0, max_lambda)

    @staticmethod
    def servers_needed(
        arrival_rate: float,
        service_rate: float,
        target_utilization: float = 0.7,
    ) -> int:
        """Minimum servers to keep utilization below target.

        c = ceil(lambda / (mu * target_rho))
        """
        if service_rate <= 0 or target_utilization <= 0:
            return 0

        return math.ceil(arrival_rate / (service_rate * target_utilization))
