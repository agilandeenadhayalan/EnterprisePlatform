"""
Tests for the Ground Truth Collector service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_labels_all(client: AsyncClient):
    resp = await client.get("/ground-truth/labels", params={"limit": 200})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 50  # ~70% of 150 = ~105


@pytest.mark.anyio
async def test_list_labels_filter_by_model(client: AsyncClient):
    resp = await client.get("/ground-truth/labels", params={"model_name": "fare_predictor", "limit": 200})
    assert resp.status_code == 200
    data = resp.json()
    for label in data["labels"]:
        assert label["model_name"] == "fare_predictor"
    assert data["total"] > 0


@pytest.mark.anyio
async def test_list_labels_limit(client: AsyncClient):
    resp = await client.get("/ground-truth/labels", params={"limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5


@pytest.mark.anyio
async def test_submit_labels(client: AsyncClient):
    payload = {
        "labels": [
            {"prediction_id": "new-pred-001", "model_name": "fare_predictor", "actual_value": 12.50},
            {"prediction_id": "new-pred-002", "model_name": "fare_predictor", "actual_value": 18.75},
        ]
    }
    resp = await client.post("/ground-truth/labels", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ingested"] == 2


@pytest.mark.anyio
async def test_submit_labels_increases_count(client: AsyncClient):
    initial = await client.get("/ground-truth/labels", params={"model_name": "fare_predictor", "limit": 200})
    initial_count = initial.json()["total"]

    payload = {
        "labels": [
            {"prediction_id": "extra-001", "model_name": "fare_predictor", "actual_value": 10.0},
        ]
    }
    await client.post("/ground-truth/labels", json=payload)

    after = await client.get("/ground-truth/labels", params={"model_name": "fare_predictor", "limit": 200})
    assert after.json()["total"] == initial_count + 1


@pytest.mark.anyio
async def test_join_fare_predictor(client: AsyncClient):
    payload = {"model_name": "fare_predictor"}
    resp = await client.post("/ground-truth/join", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_name"] == "fare_predictor"
    assert data["total"] > 0
    for pair in data["pairs"]:
        assert pair["model_name"] == "fare_predictor"
        assert "predicted_value" in pair
        assert "actual_value" in pair
        assert pair["error"] >= 0


@pytest.mark.anyio
async def test_join_eta_predictor(client: AsyncClient):
    payload = {"model_name": "eta_predictor"}
    resp = await client.post("/ground-truth/join", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_name"] == "eta_predictor"
    assert data["total"] > 0


@pytest.mark.anyio
async def test_join_nonexistent_model(client: AsyncClient):
    payload = {"model_name": "nonexistent_model"}
    resp = await client.post("/ground-truth/join", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["pairs"] == []


@pytest.mark.anyio
async def test_join_error_computation(client: AsyncClient):
    """Error should be absolute difference between predicted and actual."""
    payload = {"model_name": "fare_predictor"}
    resp = await client.post("/ground-truth/join", json=payload)
    data = resp.json()
    for pair in data["pairs"]:
        expected_error = round(abs(pair["predicted_value"] - pair["actual_value"]), 4)
        assert pair["error"] == expected_error


@pytest.mark.anyio
async def test_coverage(client: AsyncClient):
    resp = await client.get("/ground-truth/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_models"] == 3
    for cov in data["coverage"]:
        assert cov["total_predictions"] == 50
        assert cov["labeled_predictions"] > 0
        assert 0 < cov["coverage_pct"] <= 100


@pytest.mark.anyio
async def test_coverage_models_present(client: AsyncClient):
    resp = await client.get("/ground-truth/coverage")
    data = resp.json()
    model_names = [c["model_name"] for c in data["coverage"]]
    assert "fare_predictor" in model_names
    assert "eta_predictor" in model_names
    assert "demand_predictor" in model_names


@pytest.mark.anyio
async def test_coverage_percentage_reasonable(client: AsyncClient):
    resp = await client.get("/ground-truth/coverage")
    data = resp.json()
    for cov in data["coverage"]:
        # ~70% coverage expected
        assert cov["coverage_pct"] > 40
        assert cov["coverage_pct"] < 100


@pytest.mark.anyio
async def test_performance(client: AsyncClient):
    resp = await client.get("/ground-truth/performance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_models"] == 3
    for model in data["models"]:
        assert model["overall_mae"] > 0
        assert len(model["buckets"]) > 0


@pytest.mark.anyio
async def test_performance_has_buckets(client: AsyncClient):
    resp = await client.get("/ground-truth/performance")
    data = resp.json()
    for model in data["models"]:
        for bucket in model["buckets"]:
            assert "bucket" in bucket
            assert "mae" in bucket
            assert "count" in bucket
            assert bucket["count"] > 0


@pytest.mark.anyio
async def test_submit_then_join(client: AsyncClient):
    """Submitted labels should be joinable."""
    # Submit a label for an existing prediction
    payload = {
        "labels": [
            {"prediction_id": "fare_predictor-pred-000", "model_name": "fare_predictor", "actual_value": 99.99},
        ]
    }
    await client.post("/ground-truth/labels", json=payload)

    join_resp = await client.post("/ground-truth/join", json={"model_name": "fare_predictor"})
    data = join_resp.json()
    pred_ids = [p["prediction_id"] for p in data["pairs"]]
    assert "fare_predictor-pred-000" in pred_ids
