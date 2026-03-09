"""
Domain models for the Health Check service.
"""


class ServiceProbe:
    """A health check probe configuration for a service."""

    def __init__(
        self,
        id: str,
        service_name: str,
        probe_type: str,
        endpoint: str,
        timeout_seconds: int = 5,
        interval_seconds: int = 30,
        is_active: bool = True,
    ):
        self.id = id
        self.service_name = service_name
        self.probe_type = probe_type
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.interval_seconds = interval_seconds
        self.is_active = is_active

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "service_name": self.service_name,
            "probe_type": self.probe_type,
            "endpoint": self.endpoint,
            "timeout_seconds": self.timeout_seconds,
            "interval_seconds": self.interval_seconds,
            "is_active": self.is_active,
        }


class HealthCheckResult:
    """Result of a single health check execution."""

    def __init__(
        self,
        id: str,
        probe_id: str,
        service_name: str,
        status: str,
        response_time_ms: float,
        message: str = "",
        checked_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.probe_id = probe_id
        self.service_name = service_name
        self.status = status
        self.response_time_ms = response_time_ms
        self.message = message
        self.checked_at = checked_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "probe_id": self.probe_id,
            "service_name": self.service_name,
            "status": self.status,
            "response_time_ms": self.response_time_ms,
            "message": self.message,
            "checked_at": self.checked_at,
        }


class DependencyNode:
    """A node in the service dependency graph."""

    def __init__(
        self,
        service_name: str,
        dependencies: list[str],
        status: str = "healthy",
    ):
        self.service_name = service_name
        self.dependencies = dependencies
        self.status = status

    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "dependencies": self.dependencies,
            "status": self.status,
        }
