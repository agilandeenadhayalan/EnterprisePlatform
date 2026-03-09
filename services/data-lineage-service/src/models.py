"""
Domain models for the data lineage service.

Represents a directed graph of data flow: source -> transform -> destination.
"""

from datetime import datetime
from typing import Any, Optional


class LineageEdge:
    """A directed edge in the lineage graph: source -> target."""

    def __init__(
        self,
        id: str,
        source_dataset_id: str,
        target_dataset_id: str,
        transformation: str,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.source_dataset_id = source_dataset_id
        self.target_dataset_id = target_dataset_id
        self.transformation = transformation
        self.description = description or ""
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_dataset_id": self.source_dataset_id,
            "target_dataset_id": self.target_dataset_id,
            "transformation": self.transformation,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class LineageNode:
    """A node in the lineage graph representing a dataset."""

    def __init__(self, dataset_id: str, upstream: list[str] = None, downstream: list[str] = None):
        self.dataset_id = dataset_id
        self.upstream = upstream or []
        self.downstream = downstream or []

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "upstream": self.upstream,
            "downstream": self.downstream,
        }


class LineageGraph:
    """The complete lineage graph."""

    def __init__(self, nodes: list[LineageNode], edges: list[LineageEdge]):
        self.nodes = nodes
        self.edges = edges

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }
