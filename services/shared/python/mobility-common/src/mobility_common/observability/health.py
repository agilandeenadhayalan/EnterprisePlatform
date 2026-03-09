"""
Health check probe execution for service readiness and liveness.

This module provides a framework for defining and executing health check
probes against service dependencies. Health checks are a critical component
of any production deployment, answering the fundamental question: "Is this
service able to do its job right now?"

Health Check Types
------------------
Kubernetes and most container orchestrators define two primary health check
categories:

- **Liveness probes**: "Is the process alive and not deadlocked?" A failing
  liveness probe triggers a container restart.
- **Readiness probes**: "Can this service handle requests right now?" A
  failing readiness probe removes the service from the load balancer until
  it recovers (but does not restart it).

This module's ``HealthProbe`` and ``HealthChecker`` classes can be used to
implement both types by checking dependencies (databases, message brokers,
external APIs) and reporting their status.

Health Statuses
---------------
- **healthy**: The dependency is reachable and responding within acceptable
  latency thresholds.
- **unhealthy**: The dependency is unreachable, returning errors, or
  responding too slowly. The service cannot function correctly.
- **degraded**: The dependency is reachable but not performing optimally
  (e.g., elevated latency, partial functionality). The service can continue
  but operators should investigate.

Usage Example
-------------
    checker = HealthChecker()

    # Define probes for service dependencies
    checker.add_probe(HealthProbe(
        name="clickhouse",
        probe_type="tcp",
        target="clickhouse:9000",
    ))
    checker.add_probe(HealthProbe(
        name="kafka",
        probe_type="tcp",
        target="kafka:9092",
    ))
    checker.add_probe(HealthProbe(
        name="config-api",
        probe_type="http",
        target="http://config-api:8080/health",
    ))

    # Run all checks
    results = checker.check_all()

    # Determine overall health
    if checker.is_healthy():
        print("All dependencies healthy")
    else:
        for r in results:
            if r.status != "healthy":
                print(f"UNHEALTHY: {r.probe_name} - {r.message}")
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


class HealthProbe:
    """Definition of a single health check probe.

    A probe describes *what* to check and *how* to check it. The actual
    execution of the check is handled by ``HealthChecker``.

    Parameters
    ----------
    name : str
        A unique, human-readable name for this probe (e.g., "clickhouse",
        "kafka-broker", "redis-cache").
    probe_type : str
        The protocol used for the health check. Supported values:
        ``"http"`` (HTTP GET to target URL), ``"tcp"`` (TCP connection to
        target host:port), ``"grpc"`` (gRPC health check).
    target : str
        The endpoint to check. Format depends on ``probe_type``:
        - HTTP: a full URL (e.g., ``"http://service:8080/health"``)
        - TCP: ``"host:port"`` (e.g., ``"clickhouse:9000"``)
        - gRPC: ``"host:port"`` (e.g., ``"service:50051"``)
    timeout_seconds : float
        Maximum time to wait for a response before marking the probe as
        unhealthy. Default: 5.0 seconds.
    interval_seconds : float
        How often this probe should be executed in a continuous health
        checking loop. Default: 30.0 seconds.
    """

    def __init__(
        self,
        name: str,
        probe_type: str,
        target: str,
        timeout_seconds: float = 5.0,
        interval_seconds: float = 30.0,
    ) -> None:
        if probe_type not in ("http", "tcp", "grpc"):
            raise ValueError(
                f"Unsupported probe type: {probe_type!r}. "
                f"Must be one of: 'http', 'tcp', 'grpc'."
            )
        self.name = name
        self.probe_type = probe_type
        self.target = target
        self.timeout_seconds = timeout_seconds
        self.interval_seconds = interval_seconds

    def to_dict(self) -> Dict:
        """Serialize the probe definition to a dictionary.

        Returns
        -------
        dict
            The probe configuration including name, type, target, and
            timing parameters.
        """
        return {
            "name": self.name,
            "probe_type": self.probe_type,
            "target": self.target,
            "timeout_seconds": self.timeout_seconds,
            "interval_seconds": self.interval_seconds,
        }

    def __repr__(self) -> str:
        return (
            f"HealthProbe(name={self.name!r}, type={self.probe_type!r}, "
            f"target={self.target!r})"
        )


class HealthResult:
    """The outcome of executing a health check probe.

    Each ``HealthResult`` captures the status, response time, and any
    diagnostic message from a single probe execution.

    Parameters
    ----------
    probe_name : str
        The name of the probe that was executed.
    status : str
        The health status: ``"healthy"``, ``"unhealthy"``, or ``"degraded"``.
    response_time_ms : float
        The time taken to complete the check, in milliseconds.
    message : str
        A human-readable description of the result (e.g., "HTTP 200 OK",
        "Connection refused", "Timeout after 5000ms").
    checked_at : str
        ISO 8601 timestamp of when the check was performed.
    """

    def __init__(
        self,
        probe_name: str,
        status: str,
        response_time_ms: float,
        message: str,
        checked_at: str,
    ) -> None:
        if status not in ("healthy", "unhealthy", "degraded"):
            raise ValueError(
                f"Invalid health status: {status!r}. "
                f"Must be one of: 'healthy', 'unhealthy', 'degraded'."
            )
        self.probe_name = probe_name
        self.status = status
        self.response_time_ms = response_time_ms
        self.message = message
        self.checked_at = checked_at

    def to_dict(self) -> Dict:
        """Serialize the health result to a dictionary.

        Returns
        -------
        dict
            The check result including probe name, status, response time,
            message, and timestamp.
        """
        return {
            "probe_name": self.probe_name,
            "status": self.status,
            "response_time_ms": self.response_time_ms,
            "message": self.message,
            "checked_at": self.checked_at,
        }

    def __repr__(self) -> str:
        return (
            f"HealthResult(probe={self.probe_name!r}, "
            f"status={self.status!r}, "
            f"response_time_ms={self.response_time_ms:.1f})"
        )


class HealthChecker:
    """Executes health check probes and tracks their results.

    The ``HealthChecker`` maintains a registry of probes and their most
    recent results. It provides methods to run individual checks, run all
    checks at once, and determine the overall health status of the service.

    In a typical deployment, a ``HealthChecker`` is configured at service
    startup with probes for each critical dependency. A health endpoint
    (e.g., ``GET /health``) calls ``check_all()`` and returns the results.
    Container orchestrators (Kubernetes, ECS) poll this endpoint to make
    scheduling decisions.

    Note
    ----
    The ``check()`` method in this implementation simulates health checks
    rather than making real network connections. This allows the library
    to be used in tests and development environments without requiring
    actual dependencies to be running. In production, subclass or replace
    the check logic with real HTTP/TCP/gRPC clients.
    """

    def __init__(self) -> None:
        self._probes: List[HealthProbe] = []
        self._results: List[HealthResult] = []

    def add_probe(self, probe: HealthProbe) -> None:
        """Register a health check probe.

        Parameters
        ----------
        probe : HealthProbe
            The probe definition to add to the checker.
        """
        self._probes.append(probe)

    def check(self, probe_name: str) -> HealthResult:
        """Execute a single health check probe by name.

        This method simulates a health check and produces a ``HealthResult``.
        The simulation logic:

        - If the probe target contains the string ``"unhealthy"``, the check
          returns an ``"unhealthy"`` status (useful for testing failure paths).
        - For HTTP probes: simulates a response time of 5-50ms.
        - For TCP probes: simulates a response time of 1-10ms.
        - For gRPC probes: simulates a response time of 3-30ms.

        Parameters
        ----------
        probe_name : str
            The name of a previously registered probe.

        Returns
        -------
        HealthResult
            The result of the simulated check.

        Raises
        ------
        ValueError
            If no probe with the given name is registered.
        """
        probe = None
        for p in self._probes:
            if p.name == probe_name:
                probe = p
                break

        if probe is None:
            raise ValueError(
                f"No probe registered with name {probe_name!r}. "
                f"Registered probes: {[p.name for p in self._probes]}"
            )

        checked_at = datetime.now(timezone.utc).isoformat()

        # Simulate unhealthy targets for testing
        if "unhealthy" in probe.target.lower():
            result = HealthResult(
                probe_name=probe.name,
                status="unhealthy",
                response_time_ms=probe.timeout_seconds * 1000,
                message=f"Connection to {probe.target} failed: timeout after "
                        f"{probe.timeout_seconds}s",
                checked_at=checked_at,
            )
            self._results.append(result)
            return result

        # Simulate healthy responses with realistic latencies
        if probe.probe_type == "http":
            response_time_ms = random.uniform(5.0, 50.0)
            message = f"HTTP 200 OK from {probe.target}"
        elif probe.probe_type == "tcp":
            response_time_ms = random.uniform(1.0, 10.0)
            message = f"TCP connection to {probe.target} succeeded"
        else:  # grpc
            response_time_ms = random.uniform(3.0, 30.0)
            message = f"gRPC health check to {probe.target} returned SERVING"

        result = HealthResult(
            probe_name=probe.name,
            status="healthy",
            response_time_ms=round(response_time_ms, 2),
            message=message,
            checked_at=checked_at,
        )
        self._results.append(result)
        return result

    def check_all(self) -> List[HealthResult]:
        """Execute all registered health check probes.

        Returns
        -------
        list of HealthResult
            One result per registered probe, in registration order.
        """
        results: List[HealthResult] = []
        for probe in self._probes:
            result = self.check(probe.name)
            results.append(result)
        return results

    def is_healthy(self) -> bool:
        """Determine overall service health from the latest probe results.

        The service is considered healthy only if the most recent result for
        every registered probe has a ``"healthy"`` status. If any probe's
        latest result is ``"unhealthy"`` or ``"degraded"``, this returns
        ``False``.

        If a probe has never been checked, it is not considered (i.e., the
        absence of a result does not make the service unhealthy).

        Returns
        -------
        bool
            ``True`` if all latest results are healthy, ``False`` otherwise.
        """
        # Find the latest result for each probe
        latest: Dict[str, HealthResult] = {}
        for result in self._results:
            latest[result.probe_name] = result

        if not latest:
            return True  # No results yet; assume healthy

        return all(r.status == "healthy" for r in latest.values())

    def get_results(self, probe_name: Optional[str] = None) -> List[HealthResult]:
        """Retrieve stored health check results with optional filtering.

        Parameters
        ----------
        probe_name : str, optional
            If provided, only return results for the specified probe.

        Returns
        -------
        list of HealthResult
            The matching results, in chronological order.
        """
        if probe_name is not None:
            return [r for r in self._results if r.probe_name == probe_name]
        return list(self._results)

    def __repr__(self) -> str:
        return (
            f"HealthChecker(probes={len(self._probes)}, "
            f"results={len(self._results)})"
        )
