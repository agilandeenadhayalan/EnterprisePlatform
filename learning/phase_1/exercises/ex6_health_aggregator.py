"""
Exercise 6: Service Health Check Aggregator
=============================================

Build a health check aggregator that monitors multiple services
and provides a unified health status.

In a microservices platform with 155 services, the API gateway
needs to know which backends are healthy before routing traffic.
"""

from dataclasses import dataclass
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ServiceHealth:
    name: str
    status: HealthStatus
    latency_ms: float
    last_checked: float = 0.0
    error: str | None = None


class HealthAggregator:
    """
    Aggregates health status from multiple services.

    Rules for overall status:
    - HEALTHY: All services healthy
    - DEGRADED: Some services unhealthy, but critical ones are healthy
    - UNHEALTHY: Any critical service is unhealthy

    Critical services: services marked as critical (e.g., auth, postgres)
    """

    def __init__(self, critical_services: list[str] | None = None) -> None:
        self.critical_services = set(critical_services or [])
        self.services: dict[str, ServiceHealth] = {}

    def update(self, health: ServiceHealth) -> None:
        """Update the health status of a service."""
        self.services[health.name] = health

    def overall_status(self) -> HealthStatus:
        """
        Compute overall platform health.

        Rules:
        1. If any critical service is UNHEALTHY → UNHEALTHY
        2. If any non-critical service is UNHEALTHY → DEGRADED
        3. Otherwise → HEALTHY
        """
        # TODO: Implement overall status computation (~10 lines)
        raise NotImplementedError("Implement health aggregation")

    def summary(self) -> dict:
        """
        Return a summary dict with:
        - overall: HealthStatus
        - services: list of {name, status, latency_ms}
        - healthy_count, unhealthy_count
        """
        # TODO: Implement summary (~8 lines)
        raise NotImplementedError("Implement health summary")


# ── Tests ──


def test_all_healthy():
    agg = HealthAggregator(critical_services=["auth"])
    agg.update(ServiceHealth("auth", HealthStatus.HEALTHY, 5.0))
    agg.update(ServiceHealth("user", HealthStatus.HEALTHY, 10.0))
    assert agg.overall_status() == HealthStatus.HEALTHY


def test_critical_unhealthy():
    agg = HealthAggregator(critical_services=["auth"])
    agg.update(ServiceHealth("auth", HealthStatus.UNHEALTHY, 0.0, error="connection refused"))
    agg.update(ServiceHealth("user", HealthStatus.HEALTHY, 10.0))
    assert agg.overall_status() == HealthStatus.UNHEALTHY


def test_non_critical_unhealthy_is_degraded():
    agg = HealthAggregator(critical_services=["auth"])
    agg.update(ServiceHealth("auth", HealthStatus.HEALTHY, 5.0))
    agg.update(ServiceHealth("chat", HealthStatus.UNHEALTHY, 0.0))
    assert agg.overall_status() == HealthStatus.DEGRADED
