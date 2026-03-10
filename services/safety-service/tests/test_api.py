"""
Tests for the Safety Service API.

Covers: safety scores CRUD, alerts CRUD, score history, validation, edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_SCORE = {
    "entity_type": "driver",
    "entity_id": "driver-001",
    "score": 92.5,
    "factors": {"hard_braking": 2, "speeding": 0, "trips_completed": 150},
}

SAMPLE_ALERT = {
    "entity_type": "driver",
    "entity_id": "driver-001",
    "alert_type": "harsh_braking",
    "severity": "medium",
    "message": "Driver exceeded harsh braking threshold 3 times in last hour",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_safety_score(client: AsyncClient):
    """Create a safety score."""
    resp = await client.post("/safety/scores", json=SAMPLE_SCORE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["entity_type"] == "driver"
    assert data["entity_id"] == "driver-001"
    assert data["score"] == 92.5
    assert "id" in data


@pytest.mark.anyio
async def test_create_score_invalid_entity_type(client: AsyncClient):
    """Creating score with invalid entity type returns 400."""
    resp = await client.post("/safety/scores", json={
        **SAMPLE_SCORE, "entity_type": "vehicle",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_get_safety_score(client: AsyncClient):
    """Get safety score for an entity."""
    await client.post("/safety/scores", json=SAMPLE_SCORE)

    resp = await client.get("/safety/scores/driver/driver-001")
    assert resp.status_code == 200
    assert resp.json()["score"] == 92.5


@pytest.mark.anyio
async def test_get_safety_score_not_found(client: AsyncClient):
    """Getting non-existent score returns 404."""
    resp = await client.get("/safety/scores/driver/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_safety_scores(client: AsyncClient):
    """List all safety scores."""
    await client.post("/safety/scores", json=SAMPLE_SCORE)
    await client.post("/safety/scores", json={
        **SAMPLE_SCORE, "entity_type": "rider", "entity_id": "rider-001", "score": 88.0,
    })

    resp = await client.get("/safety/scores")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_score_history(client: AsyncClient):
    """Get score history for an entity."""
    await client.post("/safety/scores", json=SAMPLE_SCORE)
    await client.post("/safety/scores", json={**SAMPLE_SCORE, "score": 95.0})

    resp = await client.get("/safety/scores/driver/driver-001/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 2
    assert history[0]["score"] == 92.5
    assert history[1]["score"] == 95.0


@pytest.mark.anyio
async def test_score_history_empty(client: AsyncClient):
    """Score history for unknown entity returns empty list."""
    resp = await client.get("/safety/scores/driver/unknown/history")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_create_alert(client: AsyncClient):
    """Create a safety alert."""
    resp = await client.post("/safety/alerts", json=SAMPLE_ALERT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["alert_type"] == "harsh_braking"
    assert data["severity"] == "medium"
    assert data["status"] == "open"
    assert "id" in data


@pytest.mark.anyio
async def test_create_alert_invalid_entity_type(client: AsyncClient):
    """Creating alert with invalid entity type returns 400."""
    resp = await client.post("/safety/alerts", json={
        **SAMPLE_ALERT, "entity_type": "vehicle",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_list_alerts(client: AsyncClient):
    """List all safety alerts."""
    await client.post("/safety/alerts", json=SAMPLE_ALERT)
    await client.post("/safety/alerts", json={
        **SAMPLE_ALERT, "alert_type": "speeding", "severity": "high",
    })

    resp = await client.get("/safety/alerts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_update_alert(client: AsyncClient):
    """Update a safety alert."""
    create_resp = await client.post("/safety/alerts", json=SAMPLE_ALERT)
    alert_id = create_resp.json()["id"]

    resp = await client.patch(f"/safety/alerts/{alert_id}", json={
        "status": "resolved",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


@pytest.mark.anyio
async def test_update_alert_not_found(client: AsyncClient):
    """Updating non-existent alert returns 404."""
    resp = await client.patch("/safety/alerts/nonexistent", json={"status": "resolved"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_score_overwrites_current(client: AsyncClient):
    """Creating a new score for same entity updates the current score."""
    await client.post("/safety/scores", json=SAMPLE_SCORE)
    await client.post("/safety/scores", json={**SAMPLE_SCORE, "score": 78.0})

    resp = await client.get("/safety/scores/driver/driver-001")
    assert resp.status_code == 200
    assert resp.json()["score"] == 78.0


@pytest.mark.anyio
async def test_rider_score(client: AsyncClient):
    """Create and get a rider safety score."""
    await client.post("/safety/scores", json={
        "entity_type": "rider",
        "entity_id": "rider-042",
        "score": 95.0,
        "factors": {"cancellation_rate": 0.02, "rating": 4.9},
    })

    resp = await client.get("/safety/scores/rider/rider-042")
    assert resp.status_code == 200
    assert resp.json()["entity_type"] == "rider"
    assert resp.json()["score"] == 95.0


@pytest.mark.anyio
async def test_score_factors_included(client: AsyncClient):
    """Safety score includes factors dict."""
    resp = await client.post("/safety/scores", json=SAMPLE_SCORE)
    assert resp.status_code == 201
    factors = resp.json()["factors"]
    assert factors["hard_braking"] == 2
    assert factors["speeding"] == 0


@pytest.mark.anyio
async def test_list_scores_empty(client: AsyncClient):
    """Listing scores when none exist returns empty list."""
    resp = await client.get("/safety/scores")
    assert resp.status_code == 200
    assert resp.json() == []
