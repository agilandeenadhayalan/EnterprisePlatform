"""
Backpressure Simulation
========================

Simulates the problem of a fast producer overwhelming a slow consumer,
and demonstrates three strategies for handling the pressure.

WHY backpressure matters:
- GPS updates come 50-100/sec per driver during trips
- With 10,000 active drivers, that's 500K-1M events/sec
- If the consumer (map renderer, analytics) can't keep up,
  messages pile up in memory -> OOM crash

Strategies:
1. DROP (lossy)    — Discard excess messages. Fast, but loses data.
                     OK for location updates (latest is all that matters).
2. BUFFER (risky)  — Queue messages in memory. Preserves order but
                     can cause OOM if consumer is slow for too long.
3. THROTTLE (safe) — Slow down the producer. Preserves all data but
                     adds latency. Uses feedback loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BackpressureStrategy(str, Enum):
    DROP = "drop"
    BUFFER = "buffer"
    THROTTLE = "throttle"


@dataclass
class BackpressureStats:
    """Statistics from a backpressure simulation run."""
    strategy: BackpressureStrategy
    produced: int = 0
    consumed: int = 0
    dropped: int = 0
    buffered: int = 0
    max_buffer_size: int = 0
    producer_throttled_ticks: int = 0

    @property
    def loss_rate(self) -> float:
        """Percentage of messages lost."""
        return (self.dropped / self.produced * 100.0) if self.produced > 0 else 0.0

    @property
    def delivery_rate(self) -> float:
        """Percentage of messages successfully consumed."""
        return (self.consumed / self.produced * 100.0) if self.produced > 0 else 0.0


def simulate_backpressure(
    strategy: BackpressureStrategy,
    produce_rate: int = 100,       # Messages per tick
    consume_rate: int = 40,        # Messages per tick
    ticks: int = 20,               # Simulation duration
    max_buffer_size: int = 200,    # For buffer strategy
) -> BackpressureStats:
    """
    Simulate a producer/consumer system with backpressure.

    Args:
        strategy: Which backpressure strategy to use
        produce_rate: How many messages the producer generates per tick
        consume_rate: How many messages the consumer can process per tick
        ticks: Number of simulation time steps
        max_buffer_size: Maximum buffer capacity (buffer strategy only)

    Returns:
        BackpressureStats with simulation results
    """
    stats = BackpressureStats(strategy=strategy)
    buffer: list[int] = []  # Queue of pending messages
    current_produce_rate = produce_rate

    for tick in range(ticks):
        # ── Produce ──
        if strategy == BackpressureStrategy.THROTTLE:
            # Throttle: reduce production when buffer grows
            buffer_pressure = len(buffer) / max_buffer_size if max_buffer_size > 0 else 0
            if buffer_pressure > 0.8:
                current_produce_rate = max(consume_rate, produce_rate // 4)
                stats.producer_throttled_ticks += 1
            elif buffer_pressure > 0.5:
                current_produce_rate = max(consume_rate, produce_rate // 2)
                stats.producer_throttled_ticks += 1
            else:
                current_produce_rate = produce_rate

        produced_this_tick = current_produce_rate
        stats.produced += produced_this_tick

        if strategy == BackpressureStrategy.DROP:
            # Drop: only accept what consumer can handle + small buffer
            can_accept = consume_rate + (max_buffer_size - len(buffer))
            accepted = min(produced_this_tick, max(0, can_accept))
            dropped = produced_this_tick - accepted
            stats.dropped += dropped
            buffer.extend(range(accepted))

        elif strategy == BackpressureStrategy.BUFFER:
            # Buffer: queue everything (risk: unbounded growth)
            buffer.extend(range(produced_this_tick))
            stats.buffered += produced_this_tick

        elif strategy == BackpressureStrategy.THROTTLE:
            # Throttle: produce at reduced rate, buffer the rest
            buffer.extend(range(produced_this_tick))

        # ── Consume ──
        consumed = min(consume_rate, len(buffer))
        buffer = buffer[consumed:]
        stats.consumed += consumed

        # Track max buffer size
        stats.max_buffer_size = max(stats.max_buffer_size, len(buffer))

    return stats
