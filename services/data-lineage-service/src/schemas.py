"""
Pydantic request/response schemas for the data lineage API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class LineageEdgeCreate(BaseModel):
    """POST /lineage/edges — create a lineage edge."""
    source_dataset_id: str = Field(..., description="Source dataset ID")
    target_dataset_id: str = Field(..., description="Target dataset ID")
    transformation: str = Field(..., description="Transformation name (e.g., 'bronze_to_silver')")
    description: Optional[str] = Field(default=None, description="Description of the transformation")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional metadata")


# ── Response schemas ──

class LineageEdgeResponse(BaseModel):
    """A single lineage edge."""
    id: str
    source_dataset_id: str
    target_dataset_id: str
    transformation: str
    description: str = ""
    metadata: dict[str, Any] = {}
    created_at: datetime


class LineageNodeResponse(BaseModel):
    """A node in the lineage graph."""
    dataset_id: str
    upstream: list[str] = []
    downstream: list[str] = []


class LineageGraphResponse(BaseModel):
    """Full lineage graph."""
    nodes: list[LineageNodeResponse]
    edges: list[LineageEdgeResponse]
    node_count: int
    edge_count: int


class UpstreamDownstreamResponse(BaseModel):
    """Upstream or downstream dependencies for a dataset."""
    dataset_id: str
    datasets: list[str]
    edges: list[LineageEdgeResponse]
