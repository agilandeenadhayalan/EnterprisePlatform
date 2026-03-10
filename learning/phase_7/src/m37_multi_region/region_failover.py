"""
Region Failover — health checking, state machines, and orchestrated failover.

WHY THIS MATTERS:
When a region goes down, you need to detect it quickly and fail over traffic
to another region without data loss or extended downtime. This requires:
  - Health checking: continuously monitor each region and classify its health.
  - State machines: enforce a strict sequence of failover phases so you don't
    promote a new primary while the old one is still accepting writes.
  - Orchestration: coordinate the drain -> promote -> verify flow across
    regions, respecting cooldown periods to prevent flapping.

Key concepts:
  - Health status: healthy -> degraded -> unhealthy -> dead, based on
    consecutive failure counts and thresholds.
  - Failover phases: monitoring -> detecting -> draining -> promoting ->
    verifying -> completed. Each transition has preconditions.
  - Cooldown: minimum time between failovers to prevent flapping when
    a region oscillates between healthy and unhealthy.
"""

import time
from enum import Enum
from dataclasses import dataclass, field


class HealthStatus(Enum):
    """Region health classification."""
    healthy = "healthy"
    degraded = "degraded"
    unhealthy = "unhealthy"
    dead = "dead"


class FailoverPhase(Enum):
    """Ordered phases of a failover operation."""
    monitoring = "monitoring"
    detecting = "detecting"
    draining = "draining"
    promoting = "promoting"
    verifying = "verifying"
    completed = "completed"


# Valid phase transitions
_VALID_TRANSITIONS = {
    FailoverPhase.monitoring: {FailoverPhase.detecting},
    FailoverPhase.detecting: {FailoverPhase.draining, FailoverPhase.monitoring},
    FailoverPhase.draining: {FailoverPhase.promoting},
    FailoverPhase.promoting: {FailoverPhase.verifying},
    FailoverPhase.verifying: {FailoverPhase.completed, FailoverPhase.promoting},
    FailoverPhase.completed: {FailoverPhase.monitoring},
}


class HealthChecker:
    """Track health checks and classify region health status.

    Uses consecutive failure count with thresholds:
      0 failures      -> healthy
      1-2 failures    -> degraded
      3-4 failures    -> unhealthy
      5+ failures     -> dead
    """

    def __init__(
        self,
        degraded_threshold: int = 1,
        unhealthy_threshold: int = 3,
        dead_threshold: int = 5,
    ):
        self._degraded = degraded_threshold
        self._unhealthy = unhealthy_threshold
        self._dead = dead_threshold
        self._failures: dict[str, int] = {}
        self._total_checks: dict[str, int] = {}

    def record_check(self, region: str, success: bool) -> None:
        """Record a health check result for a region.

        Consecutive failures increment the counter. A success resets it.
        """
        if region not in self._failures:
            self._failures[region] = 0
            self._total_checks[region] = 0

        self._total_checks[region] += 1

        if success:
            self._failures[region] = 0
        else:
            self._failures[region] += 1

    def get_status(self, region: str) -> HealthStatus:
        """Return health status based on consecutive failure count."""
        failures = self._failures.get(region, 0)

        if failures >= self._dead:
            return HealthStatus.dead
        elif failures >= self._unhealthy:
            return HealthStatus.unhealthy
        elif failures >= self._degraded:
            return HealthStatus.degraded
        else:
            return HealthStatus.healthy

    def get_all_statuses(self) -> dict[str, HealthStatus]:
        """Return health status for all tracked regions."""
        return {region: self.get_status(region) for region in self._failures}


class FailoverStateMachine:
    """Enforce valid failover phase transitions.

    Prevents invalid transitions (e.g., jumping from monitoring to promoting)
    and tracks the full transition history for post-incident review.
    """

    def __init__(self, cooldown_seconds: float = 300.0):
        self._current = FailoverPhase.monitoring
        self._history: list[dict] = []
        self._cooldown_seconds = cooldown_seconds
        self._last_completed: float | None = None

    def can_transition(self, phase: FailoverPhase) -> bool:
        """Check if transitioning to the given phase is valid."""
        if phase not in _VALID_TRANSITIONS.get(self._current, set()):
            return False

        # Enforce cooldown after completion
        if (self._current == FailoverPhase.completed
                and phase == FailoverPhase.monitoring
                and self._last_completed is not None):
            if time.time() - self._last_completed < self._cooldown_seconds:
                return False

        return True

    def transition(self, phase: FailoverPhase) -> bool:
        """Execute a state transition if valid.

        Returns True if the transition succeeded, False otherwise.
        """
        if not self.can_transition(phase):
            return False

        old = self._current
        self._current = phase
        self._history.append({
            "from": old.value,
            "to": phase.value,
            "timestamp": time.time(),
        })

        if phase == FailoverPhase.completed:
            self._last_completed = time.time()

        return True

    def get_current_phase(self) -> FailoverPhase:
        """Return the current failover phase."""
        return self._current

    def get_history(self) -> list[dict]:
        """Return the full transition history."""
        return list(self._history)


class FailoverOrchestrator:
    """Orchestrate regional failover: drain -> promote -> verify.

    Manages the primary region designation and coordinates failover
    operations using the state machine to enforce correct ordering.
    """

    def __init__(self):
        self._regions: dict[str, str] = {}  # region_code -> role
        self._primary: str | None = None
        self._state_machine = FailoverStateMachine(cooldown_seconds=0)
        self._failover_log: list[dict] = []

    def add_region(self, region_code: str, is_primary: bool = False) -> None:
        """Register a region. If is_primary, designate as the primary."""
        role = "primary" if is_primary else "secondary"
        self._regions[region_code] = role
        if is_primary:
            self._primary = region_code

    def initiate_failover(self, source: str, target: str) -> bool:
        """Initiate failover from source region to target.

        Executes the full phase sequence: detecting -> draining ->
        promoting -> verifying -> completed.

        Returns True if failover completed successfully.
        """
        if source not in self._regions or target not in self._regions:
            return False

        # Walk through the failover phases
        phases = [
            FailoverPhase.detecting,
            FailoverPhase.draining,
            FailoverPhase.promoting,
            FailoverPhase.verifying,
            FailoverPhase.completed,
        ]

        for phase in phases:
            if not self._state_machine.transition(phase):
                return False

            if phase == FailoverPhase.draining:
                self._regions[source] = "draining"
            elif phase == FailoverPhase.promoting:
                self.promote_region(target)

        self._failover_log.append({
            "source": source,
            "target": target,
            "timestamp": time.time(),
        })

        # Reset to monitoring for next failover
        self._state_machine.transition(FailoverPhase.monitoring)
        return True

    def promote_region(self, region_code: str) -> None:
        """Set a region as the primary.

        Demotes the current primary (if any) to secondary.
        """
        if self._primary and self._primary in self._regions:
            self._regions[self._primary] = "secondary"
        self._regions[region_code] = "primary"
        self._primary = region_code

    def get_primary(self) -> str | None:
        """Return the current primary region code."""
        return self._primary

    def get_region_role(self, region_code: str) -> str | None:
        """Return the role of a region."""
        return self._regions.get(region_code)
