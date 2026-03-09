"""
Tests for the Prediction Logger service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_query_logs_default(client: AsyncClient):
    resp = await client.get("/predictions/log")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 50  # default limit


@pytest.mark.anyio
async def test_query_logs_all(client: AsyncClient):
    resp = await client.get("/predictions/log", params={"limit": 300})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 175  # ~200 seeded


@pytest.mark.anyio
async def test_query_logs_filter_by_model(client: AsyncClient):
    resp = await client.get("/predictions/log", params={"model": "fare_predictor", "limit": 300})
    assert resp.status_code == 200
    data = resp.json()
    for pred in data["predictions"]:
        assert pred["model_name"] == "fare_predictor"
    assert data["total"] > 0


@pytest.mark.anyio
async def test_query_logs_filter_by_date_range(client: AsyncClient):
    resp = await client.get("/predictions/log", params={
        "date_from": "2026-03-08T00:00:00Z",
        "date_to": "2026-03-08T23:59:59Z",
        "limit": 300,
    })
    assert resp.status_code == 200
    data = resp.json()
    for pred in data["predictions"]:
        assert pred["timestamp"].startswith("2026-03-08")
    assert data["total"] > 0


@pytest.mark.anyio
async def test_query_logs_limit(client: AsyncClient):
    resp = await client.get("/predictions/log", params={"limit": 5})
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


@pytest.mark.anyio
async def test_log_single_prediction(client: AsyncClient):
    payload = {
        "model_name": "fare_predictor",
        "model_version": "1.2.0",
        "features": {"trip_distance": 3.5, "pickup_zone": "zone_1", "hour": 14},
        "prediction": 12.50,
        "confidence": 0.92,
        "latency_ms": 18.5,
    }
    resp = await client.post("/predictions/log", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["message"] == "Prediction logged"


@pytest.mark.anyio
async def test_log_prediction_then_retrieve(client: AsyncClient):
    payload = {
        "model_name": "test_model",
        "model_version": "0.1.0",
        "features": {"x": 1.0},
        "prediction": 42.0,
        "confidence": 0.99,
        "latency_ms": 5.0,
    }
    create_resp = await client.post("/predictions/log", json=payload)
    log_id = create_resp.json()["id"]

    get_resp = await client.get(f"/predictions/log/{log_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["model_name"] == "test_model"
    assert data["prediction"] == 42.0


@pytest.mark.anyio
async def test_log_batch(client: AsyncClient):
    payload = {
        "predictions": [
            {
                "model_name": "fare_predictor",
                "model_version": "1.2.0",
                "features": {"trip_distance": 2.0},
                "prediction": 8.0,
                "confidence": 0.88,
                "latency_ms": 12.0,
            },
            {
                "model_name": "eta_predictor",
                "model_version": "2.0.1",
                "features": {"distance_km": 5.0},
                "prediction": 10.0,
                "confidence": 0.85,
                "latency_ms": 9.0,
            },
            {
                "model_name": "demand_predictor",
                "model_version": "1.0.3",
                "features": {"zone_id": "zone_5"},
                "prediction": 30.0,
                "confidence": 0.75,
                "latency_ms": 20.0,
            },
        ]
    }
    resp = await client.post("/predictions/log/batch", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["logged"] == 3


@pytest.mark.anyio
async def test_log_batch_increases_count(client: AsyncClient):
    initial = await client.get("/predictions/log", params={"limit": 500})
    initial_count = initial.json()["total"]

    payload = {
        "predictions": [
            {
                "model_name": "fare_predictor",
                "model_version": "1.2.0",
                "features": {"x": 1.0},
                "prediction": 10.0,
                "confidence": 0.9,
                "latency_ms": 10.0,
            },
        ]
    }
    await client.post("/predictions/log/batch", json=payload)

    after = await client.get("/predictions/log", params={"limit": 500})
    assert after.json()["total"] == initial_count + 1


@pytest.mark.anyio
async def test_get_prediction_by_id(client: AsyncClient):
    resp = await client.get("/predictions/log/plog-0000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "plog-0000"
    assert "model_name" in data
    assert "features" in data


@pytest.mark.anyio
async def test_get_prediction_not_found(client: AsyncClient):
    resp = await client.get("/predictions/log/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/predictions/log/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_models"] == 3
    for stat in data["stats"]:
        assert stat["total_predictions"] > 0
        assert stat["avg_confidence"] > 0
        assert stat["avg_latency_ms"] > 0


@pytest.mark.anyio
async def test_stats_model_names(client: AsyncClient):
    resp = await client.get("/predictions/log/stats")
    data = resp.json()
    model_names = [s["model_name"] for s in data["stats"]]
    assert "fare_predictor" in model_names
    assert "eta_predictor" in model_names
    assert "demand_predictor" in model_names


@pytest.mark.anyio
async def test_prediction_has_features(client: AsyncClient):
    resp = await client.get("/predictions/log", params={"model": "fare_predictor", "limit": 1})
    data = resp.json()
    pred = data["predictions"][0]
    assert isinstance(pred["features"], dict)
    assert len(pred["features"]) > 0


@pytest.mark.anyio
async def test_prediction_has_metadata(client: AsyncClient):
    resp = await client.get("/predictions/log/plog-0001")
    assert resp.status_code == 200
    data = resp.json()
    assert "confidence" in data
    assert "latency_ms" in data
    assert "request_source" in data
    assert "timestamp" in data
