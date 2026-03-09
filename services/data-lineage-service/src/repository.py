"""
Data Lineage repository — in-memory adjacency list for lineage graph.

Tracks data flow as a directed graph: source -> transformation -> destination.
Supports upstream/downstream traversal for impact analysis.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import LineageEdge, LineageNode, LineageGraph


class LineageRepository:
    """In-memory lineage graph storage using adjacency lists."""

    def __init__(self):
        self._edges: dict[str, LineageEdge] = {}
        # Adjacency lists: dataset_id -> set of (edge_id, neighbor_dataset_id)
        self._downstream: dict[str, set[str]] = {}  # source -> targets
        self._upstream: dict[str, set[str]] = {}  # target -> sources

    def create_edge(
        self,
        source_dataset_id: str,
        target_dataset_id: str,
        transformation: str,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> LineageEdge:
        """Create a lineage edge from source to target."""
        edge_id = str(uuid.uuid4())
        edge = LineageEdge(
            id=edge_id,
            source_dataset_id=source_dataset_id,
            target_dataset_id=target_dataset_id,
            transformation=transformation,
            description=description,
            metadata=metadata,
        )
        self._edges[edge_id] = edge

        # Update adjacency lists
        self._downstream.setdefault(source_dataset_id, set()).add(target_dataset_id)
        self._upstream.setdefault(target_dataset_id, set()).add(source_dataset_id)

        return edge

    def get_edge(self, edge_id: str) -> Optional[LineageEdge]:
        """Get a lineage edge by ID."""
        return self._edges.get(edge_id)

    def delete_edge(self, edge_id: str) -> bool:
        """Remove a lineage edge."""
        edge = self._edges.get(edge_id)
        if not edge:
            return False

        # Update adjacency lists
        source = edge.source_dataset_id
        target = edge.target_dataset_id

        if source in self._downstream:
            self._downstream[source].discard(target)
            # Check if there are other edges with the same source->target
            has_other = any(
                e.source_dataset_id == source and e.target_dataset_id == target
                for eid, e in self._edges.items() if eid != edge_id
            )
            if not has_other and target not in self._downstream.get(source, set()):
                pass  # Already discarded

        if target in self._upstream:
            self._upstream[target].discard(source)
            has_other = any(
                e.source_dataset_id == source and e.target_dataset_id == target
                for eid, e in self._edges.items() if eid != edge_id
            )
            if not has_other and source not in self._upstream.get(target, set()):
                pass  # Already discarded

        del self._edges[edge_id]
        return True

    def get_upstream(self, dataset_id: str) -> tuple[list[str], list[LineageEdge]]:
        """
        Get all upstream dependencies (recursive traversal).

        Returns (dataset_ids, edges) for all upstream sources.
        """
        visited: set[str] = set()
        result_datasets: list[str] = []
        result_edges: list[LineageEdge] = []

        def _traverse(current_id: str):
            if current_id in visited:
                return
            visited.add(current_id)

            sources = self._upstream.get(current_id, set())
            for source_id in sources:
                result_datasets.append(source_id)
                # Find edges for this relationship
                for edge in self._edges.values():
                    if edge.source_dataset_id == source_id and edge.target_dataset_id == current_id:
                        result_edges.append(edge)
                _traverse(source_id)

        _traverse(dataset_id)
        return result_datasets, result_edges

    def get_downstream(self, dataset_id: str) -> tuple[list[str], list[LineageEdge]]:
        """
        Get all downstream consumers (recursive traversal).

        Returns (dataset_ids, edges) for all downstream targets.
        """
        visited: set[str] = set()
        result_datasets: list[str] = []
        result_edges: list[LineageEdge] = []

        def _traverse(current_id: str):
            if current_id in visited:
                return
            visited.add(current_id)

            targets = self._downstream.get(current_id, set())
            for target_id in targets:
                result_datasets.append(target_id)
                # Find edges for this relationship
                for edge in self._edges.values():
                    if edge.source_dataset_id == current_id and edge.target_dataset_id == target_id:
                        result_edges.append(edge)
                _traverse(target_id)

        _traverse(dataset_id)
        return result_datasets, result_edges

    def get_full_graph(self) -> LineageGraph:
        """Get the complete lineage graph."""
        # Collect all unique dataset IDs
        all_datasets: set[str] = set()
        for edge in self._edges.values():
            all_datasets.add(edge.source_dataset_id)
            all_datasets.add(edge.target_dataset_id)

        nodes = []
        for ds_id in all_datasets:
            node = LineageNode(
                dataset_id=ds_id,
                upstream=sorted(self._upstream.get(ds_id, set())),
                downstream=sorted(self._downstream.get(ds_id, set())),
            )
            nodes.append(node)

        return LineageGraph(
            nodes=nodes,
            edges=list(self._edges.values()),
        )


# Singleton repository instance
repo = LineageRepository()
