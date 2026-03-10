"""
Tests for the Sentiment Analysis service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_analyze_positive(client: AsyncClient):
    payload = {"text": "This ride was great and the driver was excellent"}
    resp = await client.post("/sentiment/analyze", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["sentiment"] == "positive"
    assert data["score"] > 0.5


@pytest.mark.anyio
async def test_analyze_negative(client: AsyncClient):
    payload = {"text": "Terrible experience, the car was dirty and slow"}
    resp = await client.post("/sentiment/analyze", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["sentiment"] == "negative"
    assert data["score"] < 0.5


@pytest.mark.anyio
async def test_analyze_neutral(client: AsyncClient):
    payload = {"text": "I took a ride from point A to point B"}
    resp = await client.post("/sentiment/analyze", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["sentiment"] == "neutral"
    assert data["score"] == 0.50


@pytest.mark.anyio
async def test_list_results(client: AsyncClient):
    resp = await client.get("/sentiment/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["results"]) == 8


@pytest.mark.anyio
async def test_filter_sentiment(client: AsyncClient):
    resp = await client.get("/sentiment/results", params={"sentiment": "positive"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for r in data["results"]:
        assert r["sentiment"] == "positive"


@pytest.mark.anyio
async def test_get_result(client: AsyncClient):
    resp = await client.get("/sentiment/results/sent-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sentiment"] == "positive"


@pytest.mark.anyio
async def test_not_found(client: AsyncClient):
    resp = await client.get("/sentiment/results/sent-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_analyze_review(client: AsyncClient):
    payload = {
        "review_id": "review-200",
        "text": "Great driver, fast pickup, clean car",
        "entity_type": "driver",
        "entity_id": "driver-X",
    }
    resp = await client.post("/sentiment/analyze-review", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["overall_sentiment"] == "positive"
    assert data["entity_type"] == "driver"


@pytest.mark.anyio
async def test_review_has_aspects(client: AsyncClient):
    payload = {
        "review_id": "review-201",
        "text": "The driver was friendly but the car was dirty",
        "entity_type": "driver",
        "entity_id": "driver-Y",
    }
    resp = await client.post("/sentiment/analyze-review", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "aspects" in data
    assert isinstance(data["aspects"], list)


@pytest.mark.anyio
async def test_list_reviews(client: AsyncClient):
    resp = await client.get("/sentiment/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["reviews"]) == 6


@pytest.mark.anyio
async def test_get_review(client: AsyncClient):
    resp = await client.get("/sentiment/reviews/rev-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_id"] == "review-101"


@pytest.mark.anyio
async def test_review_not_found(client: AsyncClient):
    resp = await client.get("/sentiment/reviews/rev-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/sentiment/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_analyses"] == 8
    assert data["avg_score"] > 0


@pytest.mark.anyio
async def test_stats_by_sentiment(client: AsyncClient):
    resp = await client.get("/sentiment/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_sentiment"]["positive"] == 3
    assert data["by_sentiment"]["negative"] == 3
    assert data["by_sentiment"]["neutral"] == 2


@pytest.mark.anyio
async def test_score_range(client: AsyncClient):
    resp = await client.get("/sentiment/results")
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert 0.0 <= r["score"] <= 1.0
