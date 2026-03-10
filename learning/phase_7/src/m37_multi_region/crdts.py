"""
Conflict-Free Replicated Data Types (CRDTs) — convergent data structures.

WHY THIS MATTERS:
In active-active multi-region systems, you can't always coordinate writes
through a single leader. CRDTs are data structures mathematically guaranteed
to converge — every replica that has seen the same set of updates will have
the same state, regardless of the order updates were applied.

This eliminates the need for consensus protocols (Paxos/Raft) for many
use cases: counters, sets, registers, flags. The tradeoff is that CRDTs
can only model operations that are commutative, associative, and idempotent.

Key types:
  - GCounter: grow-only counter (monotonically increasing)
  - PNCounter: add and subtract using two GCounters
  - LWWRegister: last-writer-wins register (timestamp-based)
  - ORSet: observed-remove set (add-wins semantics)
  - VectorClock: partial ordering of distributed events
"""

import copy
import time
import uuid
from dataclasses import dataclass, field


class GCounter:
    """Grow-only counter CRDT.

    Each node maintains its own counter. The global value is the sum of
    all per-node counters. Merge takes the max of each node's counter,
    guaranteeing convergence.

    Properties:
      - Commutative: merge(A, B) == merge(B, A)
      - Associative: merge(merge(A, B), C) == merge(A, merge(B, C))
      - Idempotent: merge(A, A) == A
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._counters: dict[str, int] = {node_id: 0}

    def increment(self, amount: int = 1) -> None:
        """Increment this node's counter."""
        self._counters[self.node_id] = self._counters.get(self.node_id, 0) + amount

    def value(self) -> int:
        """Global counter value = sum of all per-node counters."""
        return sum(self._counters.values())

    def merge(self, other: "GCounter") -> None:
        """Merge another GCounter into this one.

        Takes the max of each node's counter — this is the key property
        that makes GCounters convergent.
        """
        for node_id, count in other._counters.items():
            self._counters[node_id] = max(
                self._counters.get(node_id, 0), count
            )

    def state(self) -> dict[str, int]:
        """Return a copy of the internal counters dict."""
        return dict(self._counters)


class PNCounter:
    """Positive-Negative counter CRDT.

    Supports both increment and decrement by using two GCounters:
    one for positive increments, one for negative. The value is
    the difference: P - N.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._positive = GCounter(node_id)
        self._negative = GCounter(node_id)

    def increment(self, amount: int = 1) -> None:
        """Increment the counter."""
        self._positive.increment(amount)

    def decrement(self, amount: int = 1) -> None:
        """Decrement the counter."""
        self._negative.increment(amount)

    def value(self) -> int:
        """Current value = positive - negative."""
        return self._positive.value() - self._negative.value()

    def merge(self, other: "PNCounter") -> None:
        """Merge by merging both internal GCounters."""
        self._positive.merge(other._positive)
        self._negative.merge(other._negative)


class LWWRegister:
    """Last-Writer-Wins Register CRDT.

    Resolves conflicts by keeping the value with the highest timestamp.
    Simple but effective — used widely in distributed databases (Cassandra).
    The tradeoff is that "last" depends on clock accuracy across regions.
    """

    def __init__(self):
        self._value: object = None
        self._timestamp: float = 0.0

    def set(self, value: object, timestamp: float | None = None) -> None:
        """Set the register value.

        Args:
            value: the value to store
            timestamp: optional explicit timestamp. Uses time.time() if None.
        """
        ts = timestamp if timestamp is not None else time.time()
        if ts >= self._timestamp:
            self._value = value
            self._timestamp = ts

    def get(self) -> object:
        """Return the current value."""
        return self._value

    def merge(self, other: "LWWRegister") -> None:
        """Merge by keeping the value with the highest timestamp."""
        if other._timestamp > self._timestamp:
            self._value = other._value
            self._timestamp = other._timestamp

    @property
    def timestamp(self) -> float:
        return self._timestamp


class ORSet:
    """Observed-Remove Set CRDT (add-wins semantics).

    The challenge with set CRDTs: if one replica adds element X and another
    concurrently removes X, what should happen? ORSet uses unique tags —
    each add creates a new tag, and remove only removes the tags it has
    observed. This gives add-wins semantics: concurrent add/remove results
    in the element being present.

    Internal representation:
      - _elements: dict mapping element -> set of unique tags
      - _tombstones: set of removed tags
    """

    def __init__(self):
        self._elements: dict[object, set[str]] = {}
        self._tombstones: set[str] = set()

    def add(self, element: object) -> None:
        """Add an element with a new unique tag."""
        tag = str(uuid.uuid4())
        if element not in self._elements:
            self._elements[element] = set()
        self._elements[element].add(tag)

    def remove(self, element: object) -> None:
        """Remove all currently observed tags for an element.

        Only tags visible to this replica are removed. If another replica
        concurrently adds the same element with a new tag, that tag will
        survive the merge (add-wins).
        """
        if element in self._elements:
            # Move all current tags to tombstones
            for tag in self._elements[element]:
                self._tombstones.add(tag)
            del self._elements[element]

    def elements(self) -> set:
        """Return the current set of elements (those with live tags)."""
        return {
            elem for elem, tags in self._elements.items()
            if tags - self._tombstones
        }

    def merge(self, other: "ORSet") -> None:
        """Merge another ORSet into this one using add-wins semantics.

        # YOUR CODE HERE
        # Design decision: add-wins means we keep an element if ANY tag for
        # it has not been tombstoned by either replica. The merge:
        #   1. Union all tombstones from both replicas
        #   2. Union all element->tags mappings from both replicas
        #   3. Remove tombstoned tags from each element's tag set
        #   4. Remove elements with no remaining live tags
        """
        # Step 1: merge tombstones (union)
        merged_tombstones = self._tombstones | other._tombstones

        # Step 2: merge element -> tags mappings (union of tags per element)
        merged_elements: dict[object, set[str]] = {}
        all_keys = set(self._elements.keys()) | set(other._elements.keys())
        for elem in all_keys:
            tags_self = self._elements.get(elem, set())
            tags_other = other._elements.get(elem, set())
            live_tags = (tags_self | tags_other) - merged_tombstones
            if live_tags:
                merged_elements[elem] = live_tags

        self._elements = merged_elements
        self._tombstones = merged_tombstones


class VectorClock:
    """Vector clock for partial ordering of distributed events.

    Each node increments its own component. Comparing two vector clocks
    tells you whether one event causally happened before another, or
    whether they are concurrent (no causal relationship).

    This is the foundation for conflict detection in distributed systems.
    """

    def __init__(self):
        self._clock: dict[str, int] = {}

    def increment(self, node_id: str) -> None:
        """Increment the clock component for this node."""
        self._clock[node_id] = self._clock.get(node_id, 0) + 1

    def merge(self, other: "VectorClock") -> None:
        """Merge by taking the component-wise maximum."""
        for node_id, value in other._clock.items():
            self._clock[node_id] = max(self._clock.get(node_id, 0), value)

    def compare(self, other: "VectorClock") -> str:
        """Compare this clock with another.

        Returns:
            "before" if this happened before other,
            "after" if this happened after other,
            "concurrent" if neither dominates,
            "equal" if they are identical.
        """
        all_keys = set(self._clock.keys()) | set(other._clock.keys())
        self_greater = False
        other_greater = False

        for key in all_keys:
            v_self = self._clock.get(key, 0)
            v_other = other._clock.get(key, 0)
            if v_self > v_other:
                self_greater = True
            elif v_other > v_self:
                other_greater = True

        if self_greater and other_greater:
            return "concurrent"
        elif self_greater:
            return "after"
        elif other_greater:
            return "before"
        else:
            return "equal"

    def state(self) -> dict[str, int]:
        """Return a copy of the clock state."""
        return dict(self._clock)
