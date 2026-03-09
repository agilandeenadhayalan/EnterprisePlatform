"""
Tests for the Prediction Service API.

Covers: single predictions, batch predictions, model loading, latency tracking,
model info, error handling, and edge cases.
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
async def test_predict_fare(client: AsyncClient):
    """Single fare prediction returns expected fields."""
    resp = await client.post("/predict", json={
        "model_name": "fare_predictor",
        "features": {"distance_miles": 5.0, "duration_minutes": 15.0, "surge_multiplier": 1.0},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "prediction" in data
    assert "confidence" in data
    assert data["model_name"] == "fare_predictor"
    assert data["model_version"] == "2.1.0"
    assert data["latency_ms"] >= 0
    assert data["prediction"] > 0


@pytest.mark.anyio
async def test_predict_demand(client: AsyncClient):
    """Single demand prediction works."""
    resp = await client.post("/predict", json={
        "model_name": "demand_predictor",
        "features": {"hour": 17, "zone_population": 80000, "is_weekend": False},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_name"] == "demand_predictor"
    assert data["prediction"] > 0
    assert 0 <= data["confidence"] <= 1.0


@pytest.mark.anyio
async def test_predict_eta(client: AsyncClient):
    """Single ETA prediction works."""
    resp = await client.post("/predict", json={
        "model_name": "eta_predictor",
        "features": {"distance_miles": 3.0, "traffic_level": 0.5, "hour": 8},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_name"] == "eta_predictor"
    assert data["prediction"] > 0


@pytest.mark.anyio
async def test_predict_missing_model(client: AsyncClient):
    """Prediction with non-existent model returns 404."""
    resp = await client.post("/predict", json={
        "model_name": "nonexistent_model",
        "features": {"x": 1},
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_predict_surge_affects_fare(client: AsyncClient):
    """Surge multiplier increases fare prediction."""
    base = await client.post("/predict", json={
        "model_name": "fare_predictor",
        "features": {"distance_miles": 5.0, "duration_minutes": 15.0, "surge_multiplier": 1.0},
    })
    surged = await client.post("/predict", json={
        "model_name": "fare_predictor",
        "features": {"distance_miles": 5.0, "duration_minutes": 15.0, "surge_multiplier": 2.0},
    })
    assert surged.json()["prediction"] > base.json()["prediction"]


@pytest.mark.anyio
async def test_predict_default_features(client: AsyncClient):
    """Prediction with empty features uses defaults."""
    resp = await client.post("/predict", json={
        "model_name": "fare_predictor",
        "features": {},
    })
    assert resp.status_code == 200
    assert resp.json()["prediction"] > 0


@pytest.mark.anyio
async def test_batch_predict(client: AsyncClient):
    """Batch prediction returns multiple results."""
    resp = await client.post("/predict/batch", json={
        "model_name": "fare_predictor",
        "instances": [
            {"distance_miles": 3.0, "duration_minutes": 10.0},
            {"distance_miles": 8.0, "duration_minutes": 25.0},
            {"distance_miles": 15.0, "duration_minutes": 40.0},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["predictions"]) == 3
    assert data["avg_latency_ms"] >= 0
    # Longer distance should cost more
    assert data["predictions"][2]["prediction"] > data["predictions"][0]["prediction"]


@pytest.mark.anyio
async def test_batch_predict_missing_model(client: AsyncClient):
    """Batch prediction with non-existent model returns 404."""
    resp = await client.post("/predict/batch", json={
        "model_name": "missing_model",
        "instances": [{"x": 1}],
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_batch_predict_single_instance(client: AsyncClient):
    """Batch prediction with one instance."""
    resp = await client.post("/predict/batch", json={
        "model_name": "eta_predictor",
        "instances": [{"distance_miles": 5.0}],
    })
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.anyio
async def test_list_models(client: AsyncClient):
    """List models returns all pre-seeded models."""
    resp = await client.get("/predict/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    names = [m["name"] for m in data["models"]]
    assert "fare_predictor" in names
    assert "demand_predictor" in names
    assert "eta_predictor" in names


@pytest.mark.anyio
async def test_model_info(client: AsyncClient):
    """Model info returns metadata and perf stats."""
    resp = await client.get("/predict/models/fare_predictor/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "fare_predictor"
    assert data["version"] == "2.1.0"
    assert data["request_count"] == 1250
    assert data["total_predictions"] == 3800


@pytest.mark.anyio
async def test_model_info_missing(client: AsyncClient):
    """Model info for non-existent model returns 404."""
    resp = await client.get("/predict/models/nonexistent/info")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_load_model_new(client: AsyncClient):
    """Loading a new model adds it to the registry."""
    resp = await client.post("/predict/models/churn_predictor/load", json={"version": "1.0.0"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "churn_predictor"
    assert data["version"] == "1.0.0"
    # Verify it appears in model list
    list_resp = await client.get("/predict/models")
    assert list_resp.json()["total"] == 4


@pytest.mark.anyio
async def test_load_model_reload(client: AsyncClient):
    """Reloading an existing model bumps its version."""
    resp = await client.post("/predict/models/fare_predictor/load", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "fare_predictor"
    assert data["version"] == "2.1.1"  # Bumped from 2.1.0
    assert data["request_count"] == 0  # Reset on reload


@pytest.mark.anyio
async def test_load_model_specific_version(client: AsyncClient):
    """Loading a model with specific version uses that version."""
    resp = await client.post("/predict/models/fare_predictor/load", json={"version": "5.0.0"})
    assert resp.status_code == 200
    assert resp.json()["version"] == "5.0.0"


@pytest.mark.anyio
async def test_latency_stats(client: AsyncClient):
    """Latency stats returns overall metrics."""
    resp = await client.get("/predict/latency")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] > 0
    assert data["overall_avg_latency_ms"] > 0
    assert len(data["models"]) == 3


@pytest.mark.anyio
async def test_predict_updates_latency(client: AsyncClient):
    """Making predictions updates latency tracking."""
    initial = await client.get("/predict/models/fare_predictor/info")
    initial_count = initial.json()["request_count"]
    await client.post("/predict", json={
        "model_name": "fare_predictor",
        "features": {"distance_miles": 5.0},
    })
    updated = await client.get("/predict/models/fare_predictor/info")
    assert updated.json()["request_count"] == initial_count + 1


@pytest.mark.anyio
async def test_batch_predict_updates_total_predictions(client: AsyncClient):
    """Batch predictions update total prediction count."""
    initial = await client.get("/predict/models/eta_predictor/info")
    initial_total = initial.json()["total_predictions"]
    await client.post("/predict/batch", json={
        "model_name": "eta_predictor",
        "instances": [{"distance_miles": 1.0}, {"distance_miles": 2.0}, {"distance_miles": 3.0}],
    })
    updated = await client.get("/predict/models/eta_predictor/info")
    assert updated.json()["total_predictions"] == initial_total + 3
