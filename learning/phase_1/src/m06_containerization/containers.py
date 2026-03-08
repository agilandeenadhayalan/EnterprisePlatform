"""
Containerization Patterns Simulator
=====================================

Demonstrates Docker concepts using Python models.
No actual Docker dependency — pure educational simulation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ContainerState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"


@dataclass
class HealthCheck:
    """
    Container health check configuration.

    WHY: Orchestrators (Docker, K8s) need to know if a container
    is ready to serve traffic. Without health checks, a container
    might be "running" but the application inside hasn't started yet.

    TYPES:
    - HTTP: GET /health → 200 OK
    - TCP: Can connect to port
    - Command: Run a command inside container
    """
    endpoint: str = "/health"
    interval_seconds: float = 10.0
    timeout_seconds: float = 5.0
    retries: int = 3
    start_period: float = 30.0  # Grace period on startup


@dataclass
class Container:
    """Simulated Docker container."""
    name: str
    image: str
    port: int
    state: ContainerState = ContainerState.CREATED
    health_check: Optional[HealthCheck] = None
    depends_on: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    memory_limit: str = "512m"
    started_at: Optional[float] = None

    def start(self) -> None:
        self.state = ContainerState.RUNNING
        self.started_at = time.time()

    def stop(self) -> None:
        self.state = ContainerState.STOPPED

    @property
    def uptime_seconds(self) -> float:
        if self.started_at:
            return time.time() - self.started_at
        return 0.0


class DockerCompose:
    """
    Simulated Docker Compose orchestrator.

    Demonstrates dependency resolution and startup ordering —
    the same logic Docker Compose uses to start services in order.
    """

    def __init__(self) -> None:
        self.containers: dict[str, Container] = {}

    def add_service(self, container: Container) -> None:
        self.containers[container.name] = container

    def resolve_startup_order(self) -> list[str]:
        """
        Topological sort of services by dependencies.

        WHY: PostgreSQL must start before auth-service,
        Redis must start before cache-dependent services, etc.
        """
        visited: set[str] = set()
        order: list[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            container = self.containers.get(name)
            if container:
                for dep in container.depends_on:
                    visit(dep)
            order.append(name)

        for name in self.containers:
            visit(name)

        return order

    def up(self) -> list[str]:
        """Start all services in dependency order."""
        order = self.resolve_startup_order()
        for name in order:
            container = self.containers.get(name)
            if container:
                container.start()
        return order
