"""
Load Patterns — generate realistic traffic patterns for performance testing.

WHY THIS MATTERS:
Performance testing with constant load misses the real-world patterns that
cause outages: sudden traffic spikes, gradual ramp-ups during launches,
and long-duration soak tests that expose memory leaks. Each pattern tests
a different failure mode:

  - Ramp: tests auto-scaling responsiveness
  - Spike: tests how the system handles sudden demand surges
  - Soak: tests for resource leaks over extended periods
  - Stress: finds the breaking point by increasing load until failure
  - Composite: chains patterns for realistic multi-phase test scenarios

Key concepts:
  - RPS (requests per second): the load intensity at any given moment
  - Pattern composition: chain patterns to model realistic traffic
  - Breaking point: the load level where latency/errors spike
"""

from dataclasses import dataclass, field


class LoadPattern:
    """Base class for load patterns.

    Subclasses implement get_rps_at() to return the target requests per
    second at any point during the test.
    """

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def duration(self) -> float:
        """Total duration of this pattern in seconds."""
        raise NotImplementedError

    def get_rps_at(self, elapsed_seconds: float) -> float:
        """Return the target RPS at the given elapsed time.

        Args:
            elapsed_seconds: time since the pattern started

        Returns:
            Target requests per second (0.0 if outside the pattern window)
        """
        raise NotImplementedError


class RampPattern(LoadPattern):
    """Linear ramp from start_rps to end_rps over duration_seconds.

    Use this to test how auto-scaling responds to gradually increasing
    traffic — e.g., a marketing campaign driving sustained growth.
    """

    def __init__(self, start_rps: float, end_rps: float, duration_seconds: float):
        self.start_rps = start_rps
        self.end_rps = end_rps
        self._duration = duration_seconds

    @property
    def duration(self) -> float:
        return self._duration

    def get_rps_at(self, elapsed_seconds: float) -> float:
        """Linear interpolation between start and end RPS."""
        if elapsed_seconds < 0 or elapsed_seconds > self._duration:
            return 0.0

        if self._duration == 0:
            return self.end_rps

        progress = elapsed_seconds / self._duration
        return self.start_rps + (self.end_rps - self.start_rps) * progress


class SpikePattern(LoadPattern):
    """Sudden spike in traffic, then return to base level.

    Models events like flash sales, viral content, or DDoS attacks.
    Tests whether circuit breakers, rate limiters, and auto-scaling
    can handle sudden demand surges.
    """

    def __init__(
        self,
        base_rps: float,
        spike_rps: float,
        spike_at: float,
        spike_duration: float,
    ):
        self.base_rps = base_rps
        self.spike_rps = spike_rps
        self.spike_at = spike_at
        self.spike_duration = spike_duration
        self._duration = spike_at + spike_duration + spike_at  # before + spike + after

    @property
    def duration(self) -> float:
        return self._duration

    def get_rps_at(self, elapsed_seconds: float) -> float:
        """Return spike_rps during the spike window, base_rps otherwise."""
        if elapsed_seconds < 0 or elapsed_seconds > self._duration:
            return 0.0

        if self.spike_at <= elapsed_seconds < self.spike_at + self.spike_duration:
            return self.spike_rps
        return self.base_rps


class SoakPattern(LoadPattern):
    """Constant load over an extended duration.

    Tests for resource leaks (memory, connections, file handles) that
    only manifest under sustained load. A soak test might run for hours
    or days at moderate load.
    """

    def __init__(self, rps: float, duration_seconds: float):
        self.rps = rps
        self._duration = duration_seconds

    @property
    def duration(self) -> float:
        return self._duration

    def get_rps_at(self, elapsed_seconds: float) -> float:
        """Constant RPS throughout the duration."""
        if elapsed_seconds < 0 or elapsed_seconds > self._duration:
            return 0.0
        return self.rps


class StressPattern(LoadPattern):
    """Step-wise load increase to find the breaking point.

    Increases load in discrete steps, holding each step long enough
    to observe steady-state behavior. Continues until max_rps.
    """

    def __init__(
        self,
        start_rps: float,
        step_rps: float,
        step_duration: float,
        max_rps: float,
    ):
        self.start_rps = start_rps
        self.step_rps = step_rps
        self.step_duration = step_duration
        self.max_rps = max_rps

        # Calculate total number of steps
        self._num_steps = 1
        current = start_rps
        while current + step_rps <= max_rps:
            current += step_rps
            self._num_steps += 1

        self._duration = self._num_steps * step_duration

    @property
    def duration(self) -> float:
        return self._duration

    def get_rps_at(self, elapsed_seconds: float) -> float:
        """Return the RPS for the current step."""
        if elapsed_seconds < 0 or elapsed_seconds > self._duration:
            return 0.0

        step_index = int(elapsed_seconds / self.step_duration)
        step_index = min(step_index, self._num_steps - 1)
        rps = self.start_rps + step_index * self.step_rps
        return min(rps, self.max_rps)


class CompositePattern(LoadPattern):
    """Chain multiple patterns sequentially.

    Models complex multi-phase test scenarios, e.g., ramp up -> spike ->
    soak -> ramp down. Each pattern starts where the previous one ended.
    """

    def __init__(self, patterns: list[LoadPattern]):
        self._patterns = patterns
        self._offsets: list[float] = []

        offset = 0.0
        for p in patterns:
            self._offsets.append(offset)
            offset += p.duration

        self._duration = offset

    @property
    def duration(self) -> float:
        return self._duration

    def get_rps_at(self, elapsed_seconds: float) -> float:
        """Delegate to the active sub-pattern based on elapsed time."""
        if elapsed_seconds < 0 or elapsed_seconds > self._duration:
            return 0.0

        for i, pattern in enumerate(self._patterns):
            pattern_start = self._offsets[i]
            pattern_end = pattern_start + pattern.duration
            if pattern_start <= elapsed_seconds <= pattern_end:
                local_time = elapsed_seconds - pattern_start
                return pattern.get_rps_at(local_time)

        return 0.0
