"""
Tests for the ETA Prediction service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_predictions(client: AsyncClient):
    resp = await client.get("/eta/predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["predictions"]) == 6


@pytest.mark.anyio
async def test_filter_by_method(client: AsyncClient):
    resp = await client.get("/eta/predictions", params={"method": "historical"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for p in data["predictions"]:
        assert p["method"] == "historical"


@pytest.mark.anyio
async def test_get_prediction(client: AsyncClient):
    resp = await client.get("/eta/predictions/pred-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["route_id"] == "route-A"
    assert data["method"] == "historical"


@pytest.mark.anyio
async def test_prediction_not_found(client: AsyncClient):
    resp = await client.get("/eta/predictions/pred-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_predict_historical(client: AsyncClient):
    payload = {
        "route_id": "route-X",
        "origin": {"lat": 40.71, "lng": -74.00},
        "destination": {"lat": 40.76, "lng": -73.98},
        "method": "historical",
    }
    resp = await client.post("/eta/predict", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["method"] == "historical"
    assert data["predicted_minutes"] > 0


@pytest.mark.anyio
async def test_predict_segment_based(client: AsyncClient):
    payload = {
        "route_id": "route-Y",
        "origin": {"lat": 40.71, "lng": -74.00},
        "destination": {"lat": 40.76, "lng": -73.98},
        "method": "segment-based",
    }
    resp = await client.post("/eta/predict", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["method"] == "segment-based"
    assert data["predicted_minutes"] > 0


@pytest.mark.anyio
async def test_predict_creates_record(client: AsyncClient):
    payload = {
        "route_id": "route-Z",
        "origin": {"lat": 40.71, "lng": -74.00},
        "destination": {"lat": 40.76, "lng": -73.98},
        "method": "graph-based",
    }
    resp = await client.post("/eta/predict", json=payload)
    assert resp.status_code == 201
    # Verify in list
    list_resp = await client.get("/eta/predictions")
    assert list_resp.json()["total"] == 7


@pytest.mark.anyio
async def test_list_segments(client: AsyncClient):
    resp = await client.get("/eta/segments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["segments"]) == 8


@pytest.mark.anyio
async def test_get_segment(client: AsyncClient):
    resp = await client.get("/eta/segments/seg-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "I-95 Highway"
    assert "speed_profiles" in data
    assert len(data["speed_profiles"]) == 3


@pytest.mark.anyio
async def test_segment_not_found(client: AsyncClient):
    resp = await client.get("/eta/segments/seg-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_record_speed(client: AsyncClient):
    payload = {"hour": 10, "speed": 55.0}
    resp = await client.post("/eta/segments/seg-001/speed", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["segment_id"] == "seg-001"
    assert data["hour"] == 10


@pytest.mark.anyio
async def test_record_speed_not_found(client: AsyncClient):
    payload = {"hour": 10, "speed": 55.0}
    resp = await client.post("/eta/segments/seg-999/speed", json=payload)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/eta/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_predictions"] == 6
    assert data["avg_confidence"] > 0


@pytest.mark.anyio
async def test_stats_by_method(client: AsyncClient):
    resp = await client.get("/eta/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_method"]["historical"] == 3
    assert data["by_method"]["segment-based"] == 2
    assert data["by_method"]["graph-based"] == 1


@pytest.mark.anyio
async def test_prediction_has_features(client: AsyncClient):
    resp = await client.get("/eta/predictions/pred-001")
    assert resp.status_code == 200
    data = resp.json()
    assert "features" in data
    assert isinstance(data["features"], dict)
    assert len(data["features"]) > 0


@pytest.mark.anyio
async def test_confidence_range(client: AsyncClient):
    resp = await client.get("/eta/predictions")
    assert resp.status_code == 200
    for p in resp.json()["predictions"]:
        assert 0.0 <= p["confidence"] <= 1.0
