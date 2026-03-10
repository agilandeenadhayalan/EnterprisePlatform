"""
Exercise 6: Data Lineage Graph Traversal
========================================
Implement BFS-based upstream and downstream tracing for a data lineage
DAG (Directed Acyclic Graph).

WHY THIS MATTERS:
When a bug appears in a dashboard metric, you need to trace back through
every transformation to find where data was corrupted. When a schema
changes in a source table, you need to know every downstream dataset
that will be affected. Data lineage is the map of your data ecosystem.

Understanding graph traversal for lineage builds intuition for:
  - BFS vs DFS for finding all reachable nodes
  - Directed graph navigation (forward vs backward edges)
  - Impact analysis (what breaks if X changes?)
  - Dependency tracking in data pipelines

YOUR TASK:
Implement two methods in LineageDAG:

1. trace_upstream(node_id) — BFS backward to find all ancestors
   - Start from node_id, follow edges backward (who feeds into this node?)
   - Return set of all ancestor node IDs (NOT including node_id itself)
   - Use collections.deque for BFS queue

2. trace_downstream(node_id) — BFS forward to find all descendants
   - Start from node_id, follow edges forward (who depends on this node?)
   - Return set of all descendant node IDs (NOT including node_id itself)
   - Use collections.deque for BFS queue

The add_node() and add_edge() methods are already implemented.
"""

from collections import deque
from dataclasses import dataclass


@dataclass
class LineageNode:
    """A node in the lineage DAG."""
    id: str
    name: str
    node_type: str  # "source", "transform", "sink"


class LineageDAG:
    """Directed Acyclic Graph for data lineage tracking."""

    def __init__(self):
        self._nodes: dict = {}
        self._forward: dict = {}   # node_id -> [child_id, ...]
        self._backward: dict = {}  # node_id -> [parent_id, ...]

    def add_node(self, node: LineageNode) -> None:
        """Add a node to the DAG."""
        self._nodes[node.id] = node
        if node.id not in self._forward:
            self._forward[node.id] = []
        if node.id not in self._backward:
            self._backward[node.id] = []

    def add_edge(self, source_id: str, target_id: str) -> None:
        """Add a directed edge from source to target."""
        if source_id not in self._forward:
            self._forward[source_id] = []
        if target_id not in self._backward:
            self._backward[target_id] = []
        if target_id not in self._forward:
            self._forward[target_id] = []
        if source_id not in self._backward:
            self._backward[source_id] = []

        self._forward[source_id].append(target_id)
        self._backward[target_id].append(source_id)

    def trace_upstream(self, node_id: str) -> set:
        """Trace all upstream ancestors using BFS.

        Starting from node_id, follow backward edges to find all
        nodes that feed into this node (directly or transitively).

        Args:
            node_id: the node to trace from

        Returns:
            Set of ancestor node IDs. Does NOT include node_id itself.

        Algorithm:
            visited = set()
            queue = deque(self._backward[node_id])  # direct parents
            add direct parents to visited
            while queue not empty:
                current = queue.popleft()
                for each parent of current (from self._backward):
                    if parent not in visited:
                        add parent to visited
                        append parent to queue
            return visited
        """
        # YOUR CODE HERE (~10 lines)
        raise NotImplementedError("Implement trace_upstream")

    def trace_downstream(self, node_id: str) -> set:
        """Trace all downstream descendants using BFS.

        Starting from node_id, follow forward edges to find all
        nodes that depend on this node (directly or transitively).

        Args:
            node_id: the node to trace from

        Returns:
            Set of descendant node IDs. Does NOT include node_id itself.

        Algorithm:
            visited = set()
            queue = deque(self._forward[node_id])  # direct children
            add direct children to visited
            while queue not empty:
                current = queue.popleft()
                for each child of current (from self._forward):
                    if child not in visited:
                        add child to visited
                        append child to queue
            return visited
        """
        # YOUR CODE HERE (~10 lines)
        raise NotImplementedError("Implement trace_downstream")


# ── Verification ──


def _make_dag():
    """Build: src -> etl -> wh -> dash, wh -> ml."""
    dag = LineageDAG()
    dag.add_node(LineageNode("src", "Raw Data", "source"))
    dag.add_node(LineageNode("etl", "ETL Job", "transform"))
    dag.add_node(LineageNode("wh", "Warehouse", "transform"))
    dag.add_node(LineageNode("dash", "Dashboard", "sink"))
    dag.add_node(LineageNode("ml", "ML Model", "sink"))
    dag.add_edge("src", "etl")
    dag.add_edge("etl", "wh")
    dag.add_edge("wh", "dash")
    dag.add_edge("wh", "ml")
    return dag


def test_direct_parent():
    """Direct parent is in upstream."""
    dag = _make_dag()
    upstream = dag.trace_upstream("etl")
    assert "src" in upstream, f"Expected 'src' in upstream of 'etl', got {upstream}"
    print("[PASS] test_direct_parent")


def test_transitive_ancestors():
    """All transitive ancestors found."""
    dag = _make_dag()
    upstream = dag.trace_upstream("dash")
    assert upstream == {"src", "etl", "wh"}, f"Expected all ancestors, got {upstream}"
    print("[PASS] test_transitive_ancestors")


def test_no_upstream():
    """Source node has no upstream."""
    dag = _make_dag()
    upstream = dag.trace_upstream("src")
    assert upstream == set(), f"Source should have no upstream, got {upstream}"
    print("[PASS] test_no_upstream")


def test_fan_out():
    """Fan-out: wh feeds both dash and ml."""
    dag = _make_dag()
    downstream = dag.trace_downstream("wh")
    assert "dash" in downstream and "ml" in downstream
    print("[PASS] test_fan_out")


def test_full_downstream():
    """Full downstream from source includes all descendants."""
    dag = _make_dag()
    downstream = dag.trace_downstream("src")
    assert downstream == {"etl", "wh", "dash", "ml"}, f"Got {downstream}"
    print("[PASS] test_full_downstream")


if __name__ == "__main__":
    test_direct_parent()
    test_transitive_ancestors()
    test_no_upstream()
    test_fan_out()
    test_full_downstream()
    print("\nAll checks passed!")
