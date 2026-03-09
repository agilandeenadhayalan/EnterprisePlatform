"""
Data Lineage Service — FastAPI application.

Tracks data flow as a directed graph: source -> transform -> destination.
Supports impact analysis via upstream/downstream traversal.

ROUTES:
  POST   /lineage/edges                   — Create a lineage edge (source->target)
  GET    /lineage/{dataset_id}/upstream    — Get upstream dependencies
  GET    /lineage/{dataset_id}/downstream  — Get downstream consumers
  GET    /lineage/graph                    — Full lineage graph
  DELETE /lineage/edges/{id}              — Remove a lineage edge
  GET    /health                          — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Data lineage tracking — directed graph of data flow",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/lineage/edges", response_model=schemas.LineageEdgeResponse, status_code=201)
async def create_edge(body: schemas.LineageEdgeCreate):
    """Create a lineage edge from source to target with transformation details."""
    edge = repository.repo.create_edge(
        source_dataset_id=body.source_dataset_id,
        target_dataset_id=body.target_dataset_id,
        transformation=body.transformation,
        description=body.description,
        metadata=body.metadata,
    )
    return schemas.LineageEdgeResponse(**edge.to_dict())


@app.get("/lineage/{dataset_id}/upstream", response_model=schemas.UpstreamDownstreamResponse)
async def get_upstream(dataset_id: str):
    """Get all upstream dependencies for a dataset (recursive traversal)."""
    datasets, edges = repository.repo.get_upstream(dataset_id)
    return schemas.UpstreamDownstreamResponse(
        dataset_id=dataset_id,
        datasets=datasets,
        edges=[schemas.LineageEdgeResponse(**e.to_dict()) for e in edges],
    )


@app.get("/lineage/{dataset_id}/downstream", response_model=schemas.UpstreamDownstreamResponse)
async def get_downstream(dataset_id: str):
    """Get all downstream consumers for a dataset (recursive traversal)."""
    datasets, edges = repository.repo.get_downstream(dataset_id)
    return schemas.UpstreamDownstreamResponse(
        dataset_id=dataset_id,
        datasets=datasets,
        edges=[schemas.LineageEdgeResponse(**e.to_dict()) for e in edges],
    )


@app.get("/lineage/graph", response_model=schemas.LineageGraphResponse)
async def get_graph():
    """Get the full lineage graph — all nodes and edges."""
    graph = repository.repo.get_full_graph()
    return schemas.LineageGraphResponse(
        nodes=[schemas.LineageNodeResponse(**n.to_dict()) for n in graph.nodes],
        edges=[schemas.LineageEdgeResponse(**e.to_dict()) for e in graph.edges],
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
    )


@app.delete("/lineage/edges/{edge_id}", status_code=204)
async def delete_edge(edge_id: str):
    """Remove a lineage edge."""
    deleted = repository.repo.delete_edge(edge_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")
