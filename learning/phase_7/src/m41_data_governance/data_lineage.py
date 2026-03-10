"""
Data lineage tracking — tracing data flow through processing pipelines.

WHY THIS MATTERS:
When a bug appears in a dashboard metric, you need to trace back through
every transformation to find where data was corrupted. When a schema
changes in a source table, you need to know every downstream dataset
that will be affected. Data lineage is the map of your data ecosystem.

For a mobility platform, lineage tracks how raw GPS events flow through
cleaning, aggregation, and ML pipelines to become trip records, driver
scores, and demand forecasts. Without lineage, debugging data issues
is guesswork.

Key concepts:
  - DAG representation: data flows form a directed acyclic graph
  - Upstream tracing: find all ancestors (data sources) for a node
  - Downstream tracing: find all descendants (consumers) of a node
  - Impact analysis: assess blast radius of a schema change
"""

from collections import deque
from dataclasses import dataclass, field


@dataclass
class DataNode:
    """A node in the lineage graph representing a dataset or transform.

    Each node has a type indicating its role in the pipeline:
    - source: raw data ingestion point (Kafka topic, S3 bucket, API)
    - transform: processing step (ETL job, Spark pipeline, ML model)
    - sink: final output (dashboard, report, ML feature store)
    """

    id: str
    name: str
    node_type: str  # "source", "transform", "sink"
    schema: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class LineageEdge:
    """A directed edge showing data flow between two nodes.

    The transform_type indicates what kind of processing occurs:
    - map: 1:1 field transformation
    - filter: subset of rows
    - join: combining two datasets
    - aggregate: grouping and summarizing
    """

    source_id: str
    target_id: str
    transform_type: str  # "map", "filter", "join", "aggregate"
    description: str = ""


class LineageGraph:
    """Directed graph of data lineage relationships.

    Supports adding nodes and edges, querying connections, and
    tracing lineage upstream (to sources) and downstream (to sinks).
    """

    def __init__(self):
        self._nodes: dict = {}
        self._edges: list = []
        self._forward: dict = {}   # source_id -> [edge, ...]
        self._backward: dict = {}  # target_id -> [edge, ...]

    def add_node(self, node: DataNode) -> None:
        """Add a data node to the lineage graph."""
        self._nodes[node.id] = node
        if node.id not in self._forward:
            self._forward[node.id] = []
        if node.id not in self._backward:
            self._backward[node.id] = []

    def add_edge(self, edge: LineageEdge) -> None:
        """Add a lineage edge (data flow) between two nodes."""
        self._edges.append(edge)
        if edge.source_id not in self._forward:
            self._forward[edge.source_id] = []
        self._forward[edge.source_id].append(edge)
        if edge.target_id not in self._backward:
            self._backward[edge.target_id] = []
        self._backward[edge.target_id].append(edge)

    def get_node(self, node_id: str) -> DataNode:
        """Get a node by its ID. Returns None if not found."""
        return self._nodes.get(node_id)

    def get_edges_from(self, node_id: str) -> list:
        """Get all outgoing edges from a node (downstream connections)."""
        return self._forward.get(node_id, [])

    def get_edges_to(self, node_id: str) -> list:
        """Get all incoming edges to a node (upstream connections)."""
        return self._backward.get(node_id, [])

    def trace_upstream(self, node_id: str) -> list:
        """Trace all upstream ancestors using BFS.

        Returns list of node IDs reachable by following edges backward
        from the given node. Does not include the node itself.
        """
        visited = set()
        queue = deque()

        # Seed with direct parents
        for edge in self._backward.get(node_id, []):
            if edge.source_id not in visited:
                visited.add(edge.source_id)
                queue.append(edge.source_id)

        while queue:
            current = queue.popleft()
            for edge in self._backward.get(current, []):
                if edge.source_id not in visited:
                    visited.add(edge.source_id)
                    queue.append(edge.source_id)

        return list(visited)

    def trace_downstream(self, node_id: str) -> list:
        """Trace all downstream descendants using BFS.

        Returns list of node IDs reachable by following edges forward
        from the given node. Does not include the node itself.
        """
        visited = set()
        queue = deque()

        for edge in self._forward.get(node_id, []):
            if edge.target_id not in visited:
                visited.add(edge.target_id)
                queue.append(edge.target_id)

        while queue:
            current = queue.popleft()
            for edge in self._forward.get(current, []):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append(edge.target_id)

        return list(visited)

    def get_full_lineage(self, node_id: str) -> dict:
        """Get both upstream and downstream lineage for a node.

        Returns:
            dict with "upstream" and "downstream" lists of node IDs.
        """
        return {
            "upstream": self.trace_upstream(node_id),
            "downstream": self.trace_downstream(node_id),
        }


class ImpactAnalyzer:
    """Analyze the impact of changes to data nodes.

    Determines which downstream datasets are affected when a source
    node changes, and identifies critical paths in the lineage graph.
    """

    def analyze_change(self, graph: LineageGraph, node_id: str) -> list:
        """Determine what downstream datasets are affected by a change.

        Returns list of node IDs that would be impacted by a schema
        or data change at the given node.
        """
        return graph.trace_downstream(node_id)

    def get_critical_paths(self, graph: LineageGraph) -> list:
        """Find paths through nodes marked as high-criticality.

        A critical path connects a source to a sink through nodes that
        have metadata["criticality"] == "high". Returns list of
        (source_id, sink_id) tuples representing critical data flows.
        """
        critical = []
        for node_id, node in graph._nodes.items():
            if node.metadata.get("criticality") == "high":
                upstream = graph.trace_upstream(node_id)
                downstream = graph.trace_downstream(node_id)
                sources = [
                    uid for uid in upstream
                    if graph.get_node(uid) and graph.get_node(uid).node_type == "source"
                ]
                sinks = [
                    did for did in downstream
                    if graph.get_node(did) and graph.get_node(did).node_type == "sink"
                ]
                # Include the node itself if it's a source or sink
                if node.node_type == "source":
                    sources.append(node_id)
                if node.node_type == "sink":
                    sinks.append(node_id)
                for src in sources:
                    for snk in sinks:
                        if (src, snk) not in critical:
                            critical.append((src, snk))
        return critical


class LineageVisualizer:
    """Simple text-based lineage visualization.

    Generates ASCII representations of lineage paths for debugging
    and documentation.
    """

    def to_ascii(self, graph: LineageGraph, node_id: str) -> str:
        """Generate a simple ASCII lineage path starting from the given node.

        Shows the node and its immediate downstream connections.
        Format:
            [node_name]
              -> [child_name] (transform_type)
              -> [child_name] (transform_type)
        """
        node = graph.get_node(node_id)
        if not node:
            return f"[unknown: {node_id}]"

        lines = [f"[{node.name}]"]
        for edge in graph.get_edges_from(node_id):
            target = graph.get_node(edge.target_id)
            target_name = target.name if target else edge.target_id
            lines.append(f"  -> [{target_name}] ({edge.transform_type})")

        return "\n".join(lines)
