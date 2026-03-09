"""
In-memory health check repository with pre-seeded data.
"""

import uuid
import random
from datetime import datetime, timezone

from models import ServiceProbe, HealthCheckResult, DependencyNode


class HealthCheckRepository:
    """In-memory store for probes, results, and dependency graph."""

    def __init__(self, seed: bool = False):
        self.probes: dict[str, ServiceProbe] = {}
        self.results: list[HealthCheckResult] = []
        self.dependency_graph: list[DependencyNode] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        probes = [
            ServiceProbe("probe-001", "auth-service", "http", "/health", 5, 30, True),
            ServiceProbe("probe-002", "user-service", "http", "/health", 5, 30, True),
            ServiceProbe("probe-003", "payment-service", "http", "/health", 5, 30, True),
            ServiceProbe("probe-004", "ride-service", "http", "/health", 5, 30, True),
            ServiceProbe("probe-005", "driver-service", "tcp", ":5432", 3, 30, True),
            ServiceProbe("probe-006", "notification-service", "http", "/health", 5, 30, True),
            ServiceProbe("probe-007", "kafka", "tcp", ":9092", 3, 15, True),
            ServiceProbe("probe-008", "redis", "tcp", ":6379", 3, 15, True),
            ServiceProbe("probe-009", "postgres", "tcp", ":5432", 3, 15, True),
            ServiceProbe("probe-010", "clickhouse", "http", "/ping", 5, 30, True),
        ]
        for p in probes:
            self.probes[p.id] = p

        # 15 results: 10 healthy, 3 unhealthy, 2 degraded
        results = [
            HealthCheckResult("res-001", "probe-001", "auth-service", "healthy", 12.3, "OK", now),
            HealthCheckResult("res-002", "probe-002", "user-service", "healthy", 8.7, "OK", now),
            HealthCheckResult("res-003", "probe-003", "payment-service", "unhealthy", 5023.0, "Connection timeout", now),
            HealthCheckResult("res-004", "probe-004", "ride-service", "healthy", 15.1, "OK", now),
            HealthCheckResult("res-005", "probe-005", "driver-service", "healthy", 3.2, "OK", now),
            HealthCheckResult("res-006", "probe-006", "notification-service", "unhealthy", 10012.0, "Service unavailable", now),
            HealthCheckResult("res-007", "probe-007", "kafka", "healthy", 2.1, "OK", now),
            HealthCheckResult("res-008", "probe-008", "redis", "healthy", 1.5, "OK", now),
            HealthCheckResult("res-009", "probe-009", "postgres", "healthy", 4.3, "OK", now),
            HealthCheckResult("res-010", "probe-010", "clickhouse", "unhealthy", 8034.0, "Connection refused", now),
            HealthCheckResult("res-011", "probe-001", "auth-service", "healthy", 11.8, "OK", now),
            HealthCheckResult("res-012", "probe-002", "user-service", "degraded", 450.0, "Slow response", now),
            HealthCheckResult("res-013", "probe-004", "ride-service", "healthy", 14.5, "OK", now),
            HealthCheckResult("res-014", "probe-007", "kafka", "degraded", 320.0, "High latency", now),
            HealthCheckResult("res-015", "probe-008", "redis", "healthy", 1.8, "OK", now),
        ]
        self.results.extend(results)

        deps = [
            DependencyNode("auth-service", ["postgres", "redis"], "healthy"),
            DependencyNode("user-service", ["postgres", "auth-service"], "healthy"),
            DependencyNode("payment-service", ["postgres", "redis", "auth-service"], "unhealthy"),
            DependencyNode("ride-service", ["postgres", "kafka", "driver-service"], "healthy"),
            DependencyNode("notification-service", ["kafka", "redis"], "unhealthy"),
        ]
        self.dependency_graph.extend(deps)

    # ── Probes ──

    def list_probes(self) -> list[ServiceProbe]:
        return list(self.probes.values())

    def get_probe(self, probe_id: str) -> ServiceProbe | None:
        return self.probes.get(probe_id)

    def create_probe(self, data: dict) -> ServiceProbe:
        probe_id = f"probe-{uuid.uuid4().hex[:8]}"
        probe = ServiceProbe(
            id=probe_id,
            service_name=data["service_name"],
            probe_type=data["probe_type"],
            endpoint=data["endpoint"],
            timeout_seconds=data.get("timeout_seconds", 5),
            interval_seconds=data.get("interval_seconds", 30),
            is_active=data.get("is_active", True),
        )
        self.probes[probe.id] = probe
        return probe

    # ── Run Check ──

    def run_check(self, probe_id: str) -> HealthCheckResult | None:
        probe = self.probes.get(probe_id)
        if not probe:
            return None
        now = datetime.now(timezone.utc).isoformat()

        # Simulate response time based on probe type
        if probe.probe_type == "http":
            response_time = round(random.uniform(5, 50), 1)
        elif probe.probe_type == "tcp":
            response_time = round(random.uniform(1, 10), 1)
        else:  # grpc
            response_time = round(random.uniform(3, 30), 1)

        # Determine status
        if "unhealthy" in probe.endpoint.lower():
            status = "unhealthy"
            message = "Check failed"
        else:
            status = "healthy"
            message = "OK"

        result = HealthCheckResult(
            id=f"res-{uuid.uuid4().hex[:8]}",
            probe_id=probe.id,
            service_name=probe.service_name,
            status=status,
            response_time_ms=response_time,
            message=message,
            checked_at=now,
        )
        self.results.append(result)
        return result

    # ── Results ──

    def list_results(self) -> list[HealthCheckResult]:
        return list(self.results)

    # ── Dashboard ──

    def get_dashboard(self) -> dict:
        """Aggregate dashboard with latest status per service."""
        service_latest: dict[str, HealthCheckResult] = {}
        for r in self.results:
            existing = service_latest.get(r.service_name)
            if not existing or r.checked_at >= existing.checked_at:
                service_latest[r.service_name] = r

        services = []
        for name, result in sorted(service_latest.items()):
            services.append({
                "name": name,
                "status": result.status,
                "last_check": result.checked_at,
                "response_time_ms": result.response_time_ms,
            })

        # Overall status: unhealthy if any unhealthy, degraded if any degraded, else healthy
        statuses = [s["status"] for s in services]
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return {"services": services, "overall_status": overall}

    # ── Dependencies ──

    def get_dependencies(self) -> list[DependencyNode]:
        return list(self.dependency_graph)

    # ── Stats ──

    def get_stats(self) -> dict:
        healthy = sum(1 for r in self.results if r.status == "healthy")
        unhealthy = sum(1 for r in self.results if r.status == "unhealthy")
        degraded = sum(1 for r in self.results if r.status == "degraded")
        avg_rt = 0.0
        if self.results:
            avg_rt = round(sum(r.response_time_ms for r in self.results) / len(self.results), 2)
        return {
            "total_probes": len(self.probes),
            "healthy_count": healthy,
            "unhealthy_count": unhealthy,
            "degraded_count": degraded,
            "avg_response_time_ms": avg_rt,
        }


REPO_CLASS = HealthCheckRepository
repo = HealthCheckRepository(seed=True)
