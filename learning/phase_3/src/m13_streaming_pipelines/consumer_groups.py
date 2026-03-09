"""
Consumer Groups & Partition Assignment
========================================

Simulates Kafka consumer group mechanics — how partitions of a topic
are distributed among consumers in a group.

KEY CONCEPTS:
- A **topic** is split into N partitions for parallelism.
- A **consumer group** is a set of consumers that cooperatively read a topic.
- Each partition is assigned to exactly ONE consumer in the group.
- When consumers join/leave, a **rebalance** redistributes partitions.

ASSIGNMENT STRATEGIES:
1. **Range** — Divides partitions into contiguous blocks per consumer.
   Fast, simple, but can be uneven (first consumer gets extras).
2. **Round-Robin** — Deals partitions one at a time like cards.
   Better balance across consumers.

LAG:
- The difference between the latest offset (newest message) and the
  committed offset (last processed message) is the consumer lag.
- High lag means the consumer is falling behind.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PartitionAssignment:
    """Result of partition assignment for a consumer group."""
    assignments: dict[str, list[int]]  # consumer_id -> [partition_ids]

    @property
    def total_partitions(self) -> int:
        return sum(len(parts) for parts in self.assignments.values())

    def consumer_for_partition(self, partition: int) -> str | None:
        """Find which consumer owns a given partition."""
        for consumer, parts in self.assignments.items():
            if partition in parts:
                return consumer
        return None


class PartitionAssigner:
    """
    Assigns topic partitions to consumers using different strategies.

    In Kafka, the group coordinator triggers assignment whenever the
    group membership changes (consumer joins or leaves).
    """

    @staticmethod
    def range_assign(partitions: list[int], consumers: list[str]) -> PartitionAssignment:
        """
        Range assignment: divide partitions into contiguous blocks.

        Algorithm:
        1. Sort partitions and consumers.
        2. Compute block_size = num_partitions // num_consumers.
        3. First (num_partitions % num_consumers) consumers get block_size + 1.

        Example with 7 partitions, 3 consumers:
            C0 -> [0, 1, 2]   (gets extra)
            C1 -> [3, 4]
            C2 -> [5, 6]
        """
        if not consumers:
            return PartitionAssignment(assignments={})

        sorted_parts = sorted(partitions)
        sorted_consumers = sorted(consumers)
        n_parts = len(sorted_parts)
        n_consumers = len(sorted_consumers)

        assignments: dict[str, list[int]] = {c: [] for c in sorted_consumers}
        block_size = n_parts // n_consumers
        extras = n_parts % n_consumers

        idx = 0
        for i, consumer in enumerate(sorted_consumers):
            size = block_size + (1 if i < extras else 0)
            assignments[consumer] = sorted_parts[idx:idx + size]
            idx += size

        return PartitionAssignment(assignments=assignments)

    @staticmethod
    def round_robin_assign(partitions: list[int], consumers: list[str]) -> PartitionAssignment:
        """
        Round-robin assignment: deal partitions one at a time.

        Algorithm:
        1. Sort partitions and consumers.
        2. Iterate partitions, assigning each to the next consumer in rotation.

        Example with 7 partitions, 3 consumers:
            C0 -> [0, 3, 6]
            C1 -> [1, 4]
            C2 -> [2, 5]
        """
        if not consumers:
            return PartitionAssignment(assignments={})

        sorted_parts = sorted(partitions)
        sorted_consumers = sorted(consumers)

        assignments: dict[str, list[int]] = {c: [] for c in sorted_consumers}
        for i, partition in enumerate(sorted_parts):
            consumer = sorted_consumers[i % len(sorted_consumers)]
            assignments[consumer].append(partition)

        return PartitionAssignment(assignments=assignments)


class ConsumerGroup:
    """
    Simulates a Kafka consumer group with automatic rebalancing.

    When consumers join or leave, the group triggers a rebalance
    using the configured assignment strategy.

    In real Kafka:
    - The group coordinator (a broker) manages membership.
    - Consumers send heartbeats to stay in the group.
    - A rebalance pauses all consumers briefly (stop-the-world).
    """

    def __init__(
        self,
        group_id: str,
        num_partitions: int,
        strategy: str = "round_robin",
    ) -> None:
        self.group_id = group_id
        self.partitions = list(range(num_partitions))
        self.strategy = strategy
        self._consumers: list[str] = []
        self._assignment: PartitionAssignment | None = None
        self._rebalance_count = 0

    @property
    def consumers(self) -> list[str]:
        return list(self._consumers)

    @property
    def assignment(self) -> PartitionAssignment | None:
        return self._assignment

    @property
    def rebalance_count(self) -> int:
        return self._rebalance_count

    def join(self, consumer_id: str) -> PartitionAssignment:
        """
        A new consumer joins the group, triggering a rebalance.

        In Kafka, this happens when a consumer calls poll() for the first time
        or after being disconnected. The group coordinator assigns a generation
        ID and triggers partition assignment.
        """
        if consumer_id in self._consumers:
            raise ValueError(f"Consumer {consumer_id} already in group {self.group_id}")
        self._consumers.append(consumer_id)
        return self._rebalance()

    def leave(self, consumer_id: str) -> PartitionAssignment:
        """
        A consumer leaves the group, triggering a rebalance.

        In Kafka, this happens when the consumer closes gracefully or when
        the coordinator detects missed heartbeats (session timeout).
        """
        if consumer_id not in self._consumers:
            raise ValueError(f"Consumer {consumer_id} not in group {self.group_id}")
        self._consumers.remove(consumer_id)
        return self._rebalance()

    def _rebalance(self) -> PartitionAssignment:
        """Redistribute partitions among current consumers."""
        self._rebalance_count += 1
        if self.strategy == "range":
            self._assignment = PartitionAssigner.range_assign(
                self.partitions, self._consumers
            )
        else:
            self._assignment = PartitionAssigner.round_robin_assign(
                self.partitions, self._consumers
            )
        return self._assignment


def compute_lag(current_offset: int, committed_offset: int) -> int:
    """
    Compute the consumer lag for a partition.

    Lag = current (latest) offset - committed (processed) offset.

    WHY lag matters:
    - Lag > 0 means the consumer is behind the producer.
    - Growing lag indicates the consumer can't keep up (need more consumers
      or faster processing).
    - Lag = 0 means the consumer is fully caught up.
    - Negative lag shouldn't happen in practice (indicates a bug).

    In production, tools like Kafka Lag Exporter or Burrow monitor this.
    """
    if committed_offset < 0:
        raise ValueError(f"Committed offset cannot be negative: {committed_offset}")
    if current_offset < 0:
        raise ValueError(f"Current offset cannot be negative: {current_offset}")
    return max(0, current_offset - committed_offset)
