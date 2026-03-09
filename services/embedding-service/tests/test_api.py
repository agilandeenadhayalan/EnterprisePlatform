"""
Tests for the Embedding service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_get_driver_embedding(client: AsyncClient):
    resp = await client.get("/embeddings/driver/driver_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "driver_001"
    assert data["entity_type"] == "driver"
    assert data["dimension"] == 8
    assert len(data["vector"]) == 8


@pytest.mark.anyio
async def test_get_zone_embedding(client: AsyncClient):
    resp = await client.get("/embeddings/zone/zone_01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_type"] == "zone"
    assert data["dimension"] == 6
    assert len(data["vector"]) == 6


@pytest.mark.anyio
async def test_get_embedding_not_found(client: AsyncClient):
    resp = await client.get("/embeddings/driver/driver_999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_embeddings_are_normalized(client: AsyncClient):
    """Pre-seeded embeddings should be L2-normalized (magnitude ~1.0)."""
    import math
    resp = await client.get("/embeddings/driver/driver_001")
    data = resp.json()
    magnitude = math.sqrt(sum(v * v for v in data["vector"]))
    assert abs(magnitude - 1.0) < 0.01


@pytest.mark.anyio
async def test_compute_embedding(client: AsyncClient):
    payload = {
        "entity_type": "rider",
        "entity_id": "rider_001",
        "features": {"trip_count": 50.0, "avg_fare": 15.0, "avg_rating": 4.5},
    }
    resp = await client.post("/embeddings/compute", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["entity_id"] == "rider_001"
    assert data["entity_type"] == "rider"
    assert data["dimension"] == 3
    assert len(data["vector"]) == 3


@pytest.mark.anyio
async def test_compute_embedding_is_normalized(client: AsyncClient):
    import math
    payload = {
        "entity_type": "rider",
        "entity_id": "rider_002",
        "features": {"x": 3.0, "y": 4.0},
    }
    resp = await client.post("/embeddings/compute", json=payload)
    data = resp.json()
    magnitude = math.sqrt(sum(v * v for v in data["vector"]))
    assert abs(magnitude - 1.0) < 0.01


@pytest.mark.anyio
async def test_compute_then_retrieve(client: AsyncClient):
    payload = {
        "entity_type": "vehicle",
        "entity_id": "vehicle_001",
        "features": {"age": 2.0, "mileage": 50000.0, "rating": 4.8},
    }
    await client.post("/embeddings/compute", json=payload)
    resp = await client.get("/embeddings/vehicle/vehicle_001")
    assert resp.status_code == 200
    assert resp.json()["entity_id"] == "vehicle_001"


@pytest.mark.anyio
async def test_similarity_drivers(client: AsyncClient):
    payload = {"entity_type": "driver", "entity_id": "driver_001", "k": 3}
    resp = await client.post("/embeddings/similarity", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["query_id"] == "driver_001"
    assert len(data["results"]) == 3
    for r in data["results"]:
        assert r["entity_id"] != "driver_001"
        assert -1.0 <= r["score"] <= 1.0


@pytest.mark.anyio
async def test_similarity_scores_ordered(client: AsyncClient):
    payload = {"entity_type": "driver", "entity_id": "driver_005", "k": 5}
    resp = await client.post("/embeddings/similarity", json=payload)
    data = resp.json()
    scores = [r["score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.anyio
async def test_similarity_zones(client: AsyncClient):
    payload = {"entity_type": "zone", "entity_id": "zone_01", "k": 3}
    resp = await client.post("/embeddings/similarity", json=payload)
    data = resp.json()
    assert len(data["results"]) == 3
    for r in data["results"]:
        assert r["entity_id"].startswith("zone_")


@pytest.mark.anyio
async def test_similarity_unknown_entity(client: AsyncClient):
    payload = {"entity_type": "driver", "entity_id": "driver_999", "k": 3}
    resp = await client.post("/embeddings/similarity", json=payload)
    data = resp.json()
    assert data["results"] == []


@pytest.mark.anyio
async def test_batch_compute(client: AsyncClient):
    payload = {
        "entities": [
            {"entity_type": "rider", "entity_id": "rider_010", "features": {"x": 1.0, "y": 2.0}},
            {"entity_type": "rider", "entity_id": "rider_011", "features": {"x": 3.0, "y": 4.0}},
            {"entity_type": "rider", "entity_id": "rider_012", "features": {"x": 5.0, "y": 6.0}},
        ]
    }
    resp = await client.post("/embeddings/batch", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["computed"] == 3
    assert len(data["embeddings"]) == 3


@pytest.mark.anyio
async def test_batch_compute_then_retrieve(client: AsyncClient):
    payload = {
        "entities": [
            {"entity_type": "test", "entity_id": "t1", "features": {"a": 1.0}},
        ]
    }
    await client.post("/embeddings/batch", json=payload)
    resp = await client.get("/embeddings/test/t1")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_knn_search(client: AsyncClient):
    payload = {"query_vector": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], "k": 5}
    resp = await client.post("/embeddings/nearest", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["k"] == 5
    assert len(data["neighbors"]) == 5
    for n in data["neighbors"]:
        assert "entity_id" in n
        assert "entity_type" in n
        assert "score" in n


@pytest.mark.anyio
async def test_knn_scores_ordered(client: AsyncClient):
    payload = {"query_vector": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "k": 10}
    resp = await client.post("/embeddings/nearest", json=payload)
    data = resp.json()
    scores = [n["score"] for n in data["neighbors"]]
    assert scores == sorted(scores, reverse=True)
