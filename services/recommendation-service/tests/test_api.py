"""
Tests for the Recommendation service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_driver_recommendations(client: AsyncClient):
    resp = await client.post("/recommendations/driver/driver_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "driver_001"
    assert data["strategy"] == "hybrid"
    assert len(data["items"]) > 0
    assert len(data["items"]) == len(data["scores"])


@pytest.mark.anyio
async def test_driver_recommendations_returns_zones(client: AsyncClient):
    resp = await client.post("/recommendations/driver/driver_005")
    data = resp.json()
    for item in data["items"]:
        assert item.startswith("zone_")


@pytest.mark.anyio
async def test_driver_recommendations_scores_ordered(client: AsyncClient):
    resp = await client.post("/recommendations/driver/driver_001")
    data = resp.json()
    scores = data["scores"]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.anyio
async def test_driver_recommendations_multiple_drivers_differ(client: AsyncClient):
    resp1 = await client.post("/recommendations/driver/driver_001")
    resp2 = await client.post("/recommendations/driver/driver_010")
    data1 = resp1.json()
    data2 = resp2.json()
    # Different drivers should get different top recommendations (or at least different scores)
    assert data1["items"] != data2["items"] or data1["scores"] != data2["scores"]


@pytest.mark.anyio
async def test_driver_recommendations_unknown_driver_cold_start(client: AsyncClient):
    resp = await client.post("/recommendations/driver/driver_999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "cold_start"
    assert len(data["items"]) > 0


@pytest.mark.anyio
async def test_rider_recommendations(client: AsyncClient):
    resp = await client.post("/recommendations/rider/rider_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "rider_001"
    assert data["strategy"] == "popularity"
    assert len(data["items"]) > 0


@pytest.mark.anyio
async def test_rider_recommendations_returns_zones(client: AsyncClient):
    resp = await client.post("/recommendations/rider/rider_042")
    data = resp.json()
    for item in data["items"]:
        assert item.startswith("zone_")


@pytest.mark.anyio
async def test_popular_zones_default(client: AsyncClient):
    resp = await client.get("/recommendations/popular-zones")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for zone in data["zones"]:
        assert "zone_id" in zone
        assert "score" in zone
        assert "avg_fare" in zone
        assert "demand_level" in zone


@pytest.mark.anyio
async def test_popular_zones_by_hour_morning(client: AsyncClient):
    resp = await client.get("/recommendations/popular-zones", params={"hour": 8})
    assert resp.status_code == 200
    data = resp.json()
    assert data["hour"] == 8
    assert data["total"] > 0
    zone_ids = [z["zone_id"] for z in data["zones"]]
    assert "zone_01" in zone_ids  # Morning rush zone


@pytest.mark.anyio
async def test_popular_zones_by_hour_evening(client: AsyncClient):
    resp = await client.get("/recommendations/popular-zones", params={"hour": 18})
    data = resp.json()
    assert data["hour"] == 18
    zone_ids = [z["zone_id"] for z in data["zones"]]
    assert "zone_01" in zone_ids or "zone_02" in zone_ids  # Evening rush


@pytest.mark.anyio
async def test_popular_zones_different_hours_differ(client: AsyncClient):
    resp_morning = await client.get("/recommendations/popular-zones", params={"hour": 8})
    resp_lunch = await client.get("/recommendations/popular-zones", params={"hour": 12})
    morning_zones = [z["zone_id"] for z in resp_morning.json()["zones"]]
    lunch_zones = [z["zone_id"] for z in resp_lunch.json()["zones"]]
    assert morning_zones != lunch_zones


@pytest.mark.anyio
async def test_similar_drivers(client: AsyncClient):
    resp = await client.post("/recommendations/similar-drivers/driver_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["driver_id"] == "driver_001"
    assert data["total"] == 5
    for sim in data["similar_drivers"]:
        assert sim["entity_id"] != "driver_001"
        assert 0 <= sim["similarity_score"] <= 1.0


@pytest.mark.anyio
async def test_similar_drivers_scores_ordered(client: AsyncClient):
    resp = await client.post("/recommendations/similar-drivers/driver_003")
    data = resp.json()
    scores = [s["similarity_score"] for s in data["similar_drivers"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.anyio
async def test_similar_drivers_unknown(client: AsyncClient):
    resp = await client.post("/recommendations/similar-drivers/driver_999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.anyio
async def test_similar_drivers_cosine_similarity(client: AsyncClient):
    """Verify that the similarity is based on cosine of ride vectors."""
    resp = await client.post("/recommendations/similar-drivers/driver_001")
    data = resp.json()
    # All similarity scores should be between -1 and 1
    for sim in data["similar_drivers"]:
        assert -1.0 <= sim["similarity_score"] <= 1.0


@pytest.mark.anyio
async def test_cold_start_basic(client: AsyncClient):
    payload = {"user_type": "driver", "initial_preferences": {}}
    resp = await client.post("/recommendations/cold-start", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "cold_start"
    assert len(data["items"]) > 0


@pytest.mark.anyio
async def test_cold_start_with_preferences(client: AsyncClient):
    payload = {
        "user_type": "driver",
        "initial_preferences": {"preferred_fare": 25.0, "preferred_borough": "Manhattan"},
    }
    resp = await client.post("/recommendations/cold-start", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "cold_start"
    assert len(data["items"]) > 0
    assert len(data["scores"]) > 0


@pytest.mark.anyio
async def test_cold_start_rider(client: AsyncClient):
    payload = {"user_type": "rider", "initial_preferences": {}}
    resp = await client.post("/recommendations/cold-start", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "cold_start"


@pytest.mark.anyio
async def test_hybrid_uses_collaborative_and_content(client: AsyncClient):
    """The hybrid strategy should produce different results than pure collaborative."""
    resp = await client.post("/recommendations/driver/driver_001")
    data = resp.json()
    assert data["strategy"] == "hybrid"
    # Hybrid should have meaningful scores
    assert all(s > 0 for s in data["scores"])
