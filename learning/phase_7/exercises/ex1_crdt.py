"""
Exercise 1: G-Counter CRDT Merge
========================================
Implement merge() for a grow-only counter CRDT.
Each node maintains its own counter. The merge takes the max of each node's counter.
This guarantees convergence: all replicas will eventually agree on the same value.

Properties to satisfy:
- Commutative: merge(A, B) == merge(B, A)
- Associative: merge(merge(A, B), C) == merge(A, merge(B, C))
- Idempotent: merge(A, A) == A

WHY THIS MATTERS:
In a multi-region system, each region tracks its own count. When regions
sync, they merge their counters. Because merge uses max (not addition),
you can merge in any order, merge duplicates, and always converge to
the correct total — without coordination.
"""


class GCounterNode:
    """A grow-only counter CRDT node.

    Internal state: a dict mapping node_id -> count.
    Each node increments only its own entry. The global value
    is the sum of all entries.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._counters: dict[str, int] = {node_id: 0}

    def increment(self, amount: int = 1) -> None:
        """Increment this node's counter."""
        self._counters[self.node_id] = self._counters.get(self.node_id, 0) + amount

    def value(self) -> int:
        """Global value = sum of all node counters."""
        return sum(self._counters.values())

    def state(self) -> dict[str, int]:
        """Return a copy of the counters dict."""
        return dict(self._counters)

    def merge(self, other_state: dict[str, int]) -> None:
        """Merge another node's state into this one.

        YOUR TASK:
        For each node_id in other_state, take the max of this node's
        counter and the other's counter. If a node_id doesn't exist
        locally, use 0 as the default.

        This ensures:
        - Commutative: merge(A, B) == merge(B, A)
        - Associative: merge(merge(A, B), C) == merge(A, merge(B, C))
        - Idempotent: merge(A, A) == A

        Hint: iterate over other_state.items() and use max().
        """
        # YOUR CODE HERE (~3 lines)
        raise NotImplementedError("Implement merge")


# ── Verification ──


def test_single_increment():
    """Single increment works."""
    n = GCounterNode("a")
    n.increment()
    assert n.value() == 1, f"Expected 1, got {n.value()}"
    print("[PASS] test_single_increment")


def test_merge_two_nodes():
    """Merge combines counters from two nodes."""
    a = GCounterNode("a")
    b = GCounterNode("b")
    a.increment(3)
    b.increment(5)
    a.merge(b.state())
    assert a.value() == 8, f"Expected 8, got {a.value()}"
    print("[PASS] test_merge_two_nodes")


def test_merge_commutative():
    """merge(A, B) produces same value as merge(B, A)."""
    a = GCounterNode("a")
    b = GCounterNode("b")
    a.increment(3)
    b.increment(7)

    a2 = GCounterNode("a")
    b2 = GCounterNode("b")
    a2.increment(3)
    b2.increment(7)

    a.merge(b.state())
    b2.merge(a2.state())
    assert a.value() == b2.value(), f"Not commutative: {a.value()} != {b2.value()}"
    print("[PASS] test_merge_commutative")


def test_merge_idempotent():
    """merge(A, A) produces A."""
    a = GCounterNode("a")
    a.increment(5)
    before = a.value()
    a.merge(a.state())
    assert a.value() == before, f"Not idempotent: {a.value()} != {before}"
    print("[PASS] test_merge_idempotent")


def test_merge_convergence():
    """All replicas converge after merging."""
    a = GCounterNode("a")
    b = GCounterNode("b")
    c = GCounterNode("c")
    a.increment(1)
    b.increment(2)
    c.increment(3)

    # All merge with each other
    a.merge(b.state())
    a.merge(c.state())
    b.merge(a.state())
    b.merge(c.state())
    c.merge(a.state())
    c.merge(b.state())

    assert a.value() == b.value() == c.value() == 6, \
        f"Not converged: a={a.value()}, b={b.value()}, c={c.value()}"
    print("[PASS] test_merge_convergence")


if __name__ == "__main__":
    test_single_increment()
    test_merge_two_nodes()
    test_merge_commutative()
    test_merge_idempotent()
    test_merge_convergence()
    print("\nAll checks passed!")
