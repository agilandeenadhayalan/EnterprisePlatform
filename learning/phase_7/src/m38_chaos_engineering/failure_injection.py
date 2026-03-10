"""
Failure Injection — simulate infrastructure failures for resilience testing.

WHY THIS MATTERS:
Production systems fail in surprising ways. Chaos engineering proactively
injects failures to discover weaknesses before they cause outages. This
module models the core failure injection primitives: network faults,
resource exhaustion, and process-level failures.

Netflix pioneered this with Chaos Monkey (random instance termination),
but modern chaos engineering is much more targeted: inject specific faults,
measure the blast radius, verify your system's resilience hypothesis.

Key concepts:
  - Failure modes: network (latency, partition, packet loss), resource
    (CPU, memory, disk), process (crash, DNS failure).
  - Injection lifecycle: inject -> observe -> rollback. Every injection
    must be reversible to prevent permanent damage.
  - Intensity: how severe the failure is (0.0 = none, 1.0 = total).
"""

import uuid
import time
import random
from enum import Enum
from dataclasses import dataclass, field


class FailureMode(Enum):
    """Types of failures that can be injected."""
    cpu_stress = "cpu_stress"
    memory_leak = "memory_leak"
    network_latency = "network_latency"
    network_partition = "network_partition"
    disk_full = "disk_full"
    process_crash = "process_crash"
    dns_failure = "dns_failure"


@dataclass
class FailureConfig:
    """Configuration for a failure injection.

    Attributes:
        mode: type of failure to inject
        duration_seconds: how long the failure lasts
        intensity: severity from 0.0 (none) to 1.0 (total)
        target_service: which service to target
        parameters: additional mode-specific parameters
    """
    mode: FailureMode
    duration_seconds: float
    intensity: float = 0.5
    target_service: str = ""
    parameters: dict = field(default_factory=dict)


class FailureInjector:
    """Manage the lifecycle of failure injections.

    Tracks active injections and supports rollback to restore
    normal operation after chaos experiments.
    """

    def __init__(self):
        self._active: dict[str, dict] = {}  # injection_id -> details

    def inject(self, config: FailureConfig) -> str:
        """Inject a failure. Returns a unique injection ID for rollback.

        Validates intensity is in [0.0, 1.0] and duration is positive.
        """
        if not 0.0 <= config.intensity <= 1.0:
            raise ValueError(f"Intensity must be 0.0-1.0, got {config.intensity}")
        if config.duration_seconds <= 0:
            raise ValueError("Duration must be positive")

        injection_id = str(uuid.uuid4())[:8]
        self._active[injection_id] = {
            "config": config,
            "injected_at": time.time(),
            "injection_id": injection_id,
        }
        return injection_id

    def rollback(self, injection_id: str) -> bool:
        """Remove an injected failure. Returns True if found and removed."""
        if injection_id in self._active:
            del self._active[injection_id]
            return True
        return False

    def get_active_injections(self) -> list[dict]:
        """Return list of all currently active failure injections."""
        return [
            {
                "injection_id": details["injection_id"],
                "mode": details["config"].mode.value,
                "target": details["config"].target_service,
                "intensity": details["config"].intensity,
            }
            for details in self._active.values()
        ]


class NetworkFault:
    """Simulate network-level failures: latency, packet loss, partitions.

    Models the effect of network degradation on request processing.
    Latency and packet loss can be stacked to simulate realistic
    network conditions.
    """

    def __init__(self):
        self._base_latency_ms: float = 0.0
        self._jitter_ms: float = 0.0
        self._packet_loss_rate: float = 0.0
        self._partitioned_services: set[str] = set()

    def add_latency(self, base_ms: float, jitter_ms: float = 0.0) -> None:
        """Add network latency with optional jitter.

        Args:
            base_ms: constant latency to add
            jitter_ms: random variation (+/- jitter_ms)
        """
        self._base_latency_ms = base_ms
        self._jitter_ms = jitter_ms

    def add_packet_loss(self, loss_rate: float) -> None:
        """Simulate packet loss.

        Args:
            loss_rate: probability of a packet being dropped (0.0 to 1.0)
        """
        if not 0.0 <= loss_rate <= 1.0:
            raise ValueError(f"Loss rate must be 0.0-1.0, got {loss_rate}")
        self._packet_loss_rate = loss_rate

    def simulate_partition(self, services: list[str]) -> None:
        """Create a network partition isolating the given services."""
        self._partitioned_services = set(services)

    def is_partitioned(self, service: str) -> bool:
        """Check if a service is in the partitioned set."""
        return service in self._partitioned_services

    def apply_to_request(self, original_latency_ms: float) -> dict:
        """Apply network faults to a request. Returns the modified metrics.

        Returns:
            dict with "latency_ms" (modified), "dropped" (bool),
            "original_latency_ms"
        """
        # Apply packet loss
        dropped = random.random() < self._packet_loss_rate

        # Apply latency
        jitter = 0.0
        if self._jitter_ms > 0:
            jitter = random.uniform(-self._jitter_ms, self._jitter_ms)

        modified_latency = original_latency_ms + self._base_latency_ms + jitter

        return {
            "latency_ms": max(0.0, modified_latency),
            "dropped": dropped,
            "original_latency_ms": original_latency_ms,
        }


class ResourceExhaustion:
    """Model resource exhaustion: CPU load, memory pressure.

    Computes the performance degradation from resource contention.
    At high utilization, response times increase non-linearly
    (queuing theory hockey stick curve).
    """

    def __init__(self):
        self._cpu_target: float = 0.0
        self._memory_target: float = 0.0

    def simulate_cpu_load(self, target_percent: float) -> None:
        """Set target CPU utilization (0-100)."""
        self._cpu_target = min(100.0, max(0.0, target_percent))

    def simulate_memory_pressure(self, target_percent: float) -> None:
        """Set target memory utilization (0-100)."""
        self._memory_target = min(100.0, max(0.0, target_percent))

    def get_impact(self) -> dict:
        """Compute the performance degradation from resource pressure.

        Returns:
            dict with cpu_degradation_factor, memory_degradation_factor,
            combined_degradation_factor (multiplicative).
            A factor of 1.0 means no degradation. Higher = worse.
        """
        # CPU: degradation follows queuing theory — exponential near 100%
        cpu_util = self._cpu_target / 100.0
        if cpu_util >= 1.0:
            cpu_factor = 50.0  # system is saturated
        elif cpu_util > 0:
            cpu_factor = 1.0 / (1.0 - cpu_util)
        else:
            cpu_factor = 1.0

        # Memory: gradual degradation, sharp increase near 100%
        mem_util = self._memory_target / 100.0
        if mem_util >= 1.0:
            mem_factor = 100.0  # OOM territory
        elif mem_util > 0.8:
            # Sharp increase in the danger zone
            mem_factor = 1.0 + (mem_util - 0.8) * 25.0
        else:
            mem_factor = 1.0 + mem_util * 0.5

        return {
            "cpu_degradation_factor": round(cpu_factor, 2),
            "memory_degradation_factor": round(mem_factor, 2),
            "combined_degradation_factor": round(cpu_factor * mem_factor, 2),
        }
