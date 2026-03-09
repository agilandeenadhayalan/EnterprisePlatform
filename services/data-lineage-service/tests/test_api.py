"""
Tests for the Data Lineage Service API.

Covers: edge CRUD, upstream/downstream traversal, graph queries, and edge cases.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_edge(client: AsyncClient):
    """Create a lineage edge between two datasets."""
    resp = await client.post("/lineage/edges", json={
        "source_dataset_id": "ds-raw-gps",
        "target_dataset_id": "ds-clean-gps",
        "transformation": "bronze_to_silver",
        "description": "Clean GPS data: remove nulls, validate coordinates",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_dataset_id"] == "ds-raw-gps"
    assert data["target_dataset_id"] == "ds-clean-gps"
    assert data["transformation"] == "bronze_to_silver"
    assert "id" in data


@pytest.mark.anyio
async def test_create_edge_with_metadata(client: AsyncClient):
    """Create a lineage edge with additional metadata."""
    resp = await client.post("/lineage/edges", json={
        "source_dataset_id": "src",
        "target_dataset_id": "tgt",
        "transformation": "etl_job",
        "metadata": {"job_name": "nightly_etl", "schedule": "0 2 * * *"},
    })
    assert resp.status_code == 201
    assert resp.json()["metadata"]["job_name"] == "nightly_etl"


@pytest.mark.anyio
async def test_delete_edge(client: AsyncClient):
    """Delete a lineage edge."""
    create_resp = await client.post("/lineage/edges", json={
        "source_dataset_id": "a",
        "target_dataset_id": "b",
        "transformation": "transform_ab",
    })
    edge_id = create_resp.json()["id"]

    resp = await client.delete(f"/lineage/edges/{edge_id}")
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_delete_edge_not_found(client: AsyncClient):
    """Deleting a non-existent edge returns 404."""
    resp = await client.delete("/lineage/edges/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_upstream_simple(client: AsyncClient):
    """Get upstream dependencies for a dataset."""
    # A -> B -> C
    await client.post("/lineage/edges", json={
        "source_dataset_id": "A",
        "target_dataset_id": "B",
        "transformation": "transform_ab",
    })
    await client.post("/lineage/edges", json={
        "source_dataset_id": "B",
        "target_dataset_id": "C",
        "transformation": "transform_bc",
    })

    resp = await client.get("/lineage/C/upstream")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_id"] == "C"
    assert "B" in data["datasets"]
    assert "A" in data["datasets"]


@pytest.mark.anyio
async def test_downstream_simple(client: AsyncClient):
    """Get downstream consumers for a dataset."""
    # A -> B -> C
    await client.post("/lineage/edges", json={
        "source_dataset_id": "A",
        "target_dataset_id": "B",
        "transformation": "transform_ab",
    })
    await client.post("/lineage/edges", json={
        "source_dataset_id": "B",
        "target_dataset_id": "C",
        "transformation": "transform_bc",
    })

    resp = await client.get("/lineage/A/downstream")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_id"] == "A"
    assert "B" in data["datasets"]
    assert "C" in data["datasets"]


@pytest.mark.anyio
async def test_upstream_no_dependencies(client: AsyncClient):
    """Dataset with no upstream returns empty list."""
    await client.post("/lineage/edges", json={
        "source_dataset_id": "root",
        "target_dataset_id": "child",
        "transformation": "ingest",
    })

    resp = await client.get("/lineage/root/upstream")
    data = resp.json()
    assert data["datasets"] == []
    assert data["edges"] == []


@pytest.mark.anyio
async def test_downstream_no_consumers(client: AsyncClient):
    """Dataset with no downstream returns empty list."""
    await client.post("/lineage/edges", json={
        "source_dataset_id": "parent",
        "target_dataset_id": "leaf",
        "transformation": "aggregate",
    })

    resp = await client.get("/lineage/leaf/downstream")
    data = resp.json()
    assert data["datasets"] == []
    assert data["edges"] == []


@pytest.mark.anyio
async def test_graph_empty(client: AsyncClient):
    """Empty lineage graph has no nodes or edges."""
    resp = await client.get("/lineage/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["node_count"] == 0
    assert data["edge_count"] == 0
    assert data["nodes"] == []
    assert data["edges"] == []


@pytest.mark.anyio
async def test_graph_with_edges(client: AsyncClient):
    """Full graph contains all nodes and edges."""
    await client.post("/lineage/edges", json={
        "source_dataset_id": "raw_rides",
        "target_dataset_id": "clean_rides",
        "transformation": "clean",
    })
    await client.post("/lineage/edges", json={
        "source_dataset_id": "clean_rides",
        "target_dataset_id": "ride_metrics",
        "transformation": "aggregate",
    })

    resp = await client.get("/lineage/graph")
    data = resp.json()
    assert data["node_count"] == 3
    assert data["edge_count"] == 2
    node_ids = [n["dataset_id"] for n in data["nodes"]]
    assert "raw_rides" in node_ids
    assert "clean_rides" in node_ids
    assert "ride_metrics" in node_ids


@pytest.mark.anyio
async def test_diamond_dependency(client: AsyncClient):
    """Handle diamond-shaped dependencies: A -> B, A -> C, B -> D, C -> D."""
    await client.post("/lineage/edges", json={
        "source_dataset_id": "A", "target_dataset_id": "B", "transformation": "t1",
    })
    await client.post("/lineage/edges", json={
        "source_dataset_id": "A", "target_dataset_id": "C", "transformation": "t2",
    })
    await client.post("/lineage/edges", json={
        "source_dataset_id": "B", "target_dataset_id": "D", "transformation": "t3",
    })
    await client.post("/lineage/edges", json={
        "source_dataset_id": "C", "target_dataset_id": "D", "transformation": "t4",
    })

    # D should have both B and C as upstream, and ultimately A
    resp = await client.get("/lineage/D/upstream")
    data = resp.json()
    assert "B" in data["datasets"]
    assert "C" in data["datasets"]
    assert "A" in data["datasets"]

    # A should have B, C, D as downstream
    resp = await client.get("/lineage/A/downstream")
    data = resp.json()
    assert "B" in data["datasets"]
    assert "C" in data["datasets"]
    assert "D" in data["datasets"]


@pytest.mark.anyio
async def test_delete_edge_updates_graph(client: AsyncClient):
    """Deleting an edge removes it from the graph."""
    resp1 = await client.post("/lineage/edges", json={
        "source_dataset_id": "X", "target_dataset_id": "Y", "transformation": "t1",
    })
    edge_id = resp1.json()["id"]

    # Graph has 1 edge
    graph = await client.get("/lineage/graph")
    assert graph.json()["edge_count"] == 1

    # Delete the edge
    await client.delete(f"/lineage/edges/{edge_id}")

    # Graph is now empty
    graph = await client.get("/lineage/graph")
    assert graph.json()["edge_count"] == 0
