"""
Tests for the AB Test Analytics service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_run_test_significant(client: AsyncClient):
    payload = {
        "experiment_id": "exp-test-1",
        "metric": "conversion",
        "control_count": 1000,
        "control_conversions": 100,
        "variant_count": 1000,
        "variant_conversions": 150,
    }
    resp = await client.post("/ab-analytics/test", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["significant"] is True
    assert data["z_score"] > 0


@pytest.mark.anyio
async def test_run_test_not_significant(client: AsyncClient):
    payload = {
        "experiment_id": "exp-test-2",
        "metric": "conversion",
        "control_count": 100,
        "control_conversions": 10,
        "variant_count": 100,
        "variant_conversions": 12,
    }
    resp = await client.post("/ab-analytics/test", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["significant"] is False


@pytest.mark.anyio
async def test_list_results(client: AsyncClient):
    resp = await client.get("/ab-analytics/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5


@pytest.mark.anyio
async def test_filter_experiment(client: AsyncClient):
    resp = await client.get("/ab-analytics/results", params={"experiment_id": "exp-001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for r in data["results"]:
        assert r["experiment_id"] == "exp-001"


@pytest.mark.anyio
async def test_get_result(client: AsyncClient):
    resp = await client.get("/ab-analytics/results/abt-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "exp-001"
    assert data["significant"] is True


@pytest.mark.anyio
async def test_get_not_found(client: AsyncClient):
    resp = await client.get("/ab-analytics/results/abt-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_power_calculation(client: AsyncClient):
    payload = {"alpha": 0.05, "power": 0.8, "mde": 0.05}
    resp = await client.post("/ab-analytics/power", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_size_needed"] > 0
    assert data["alpha"] == 0.05
    assert data["power"] == 0.8


@pytest.mark.anyio
async def test_power_small_mde_needs_more(client: AsyncClient):
    resp_large = await client.post("/ab-analytics/power", json={"alpha": 0.05, "power": 0.8, "mde": 0.10})
    resp_small = await client.post("/ab-analytics/power", json={"alpha": 0.05, "power": 0.8, "mde": 0.02})
    assert resp_small.json()["sample_size_needed"] > resp_large.json()["sample_size_needed"]


@pytest.mark.anyio
async def test_sequential_test(client: AsyncClient):
    payload = {
        "experiment_id": "exp-seq-1",
        "observations": 200,
        "successes": 100,
        "alpha": 0.05,
    }
    resp = await client.post("/ab-analytics/sequential", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["experiment_id"] == "exp-seq-1"
    assert "current_z" in data
    assert "boundary" in data


@pytest.mark.anyio
async def test_sequential_stopped_early(client: AsyncClient):
    # Very strong signal should trigger early stopping
    payload = {
        "experiment_id": "exp-seq-2",
        "observations": 1000,
        "successes": 900,
        "alpha": 0.05,
    }
    resp = await client.post("/ab-analytics/sequential", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["stopped_early"] is True


@pytest.mark.anyio
async def test_sequential_not_stopped(client: AsyncClient):
    # Balanced data should not trigger early stopping
    payload = {
        "experiment_id": "exp-seq-3",
        "observations": 100,
        "successes": 50,
        "alpha": 0.05,
    }
    resp = await client.post("/ab-analytics/sequential", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["stopped_early"] is False


@pytest.mark.anyio
async def test_list_sequential(client: AsyncClient):
    resp = await client.get("/ab-analytics/sequential")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/ab-analytics/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tests"] == 5


@pytest.mark.anyio
async def test_stats_significant_count(client: AsyncClient):
    resp = await client.get("/ab-analytics/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["significant_count"] == 3


@pytest.mark.anyio
async def test_z_score_calculation(client: AsyncClient):
    # Known z-score: p1=0.1, p2=0.15, n=1000 each
    payload = {
        "experiment_id": "exp-z",
        "metric": "ctr",
        "control_count": 1000,
        "control_conversions": 100,
        "variant_count": 1000,
        "variant_conversions": 150,
    }
    resp = await client.post("/ab-analytics/test", json=payload)
    data = resp.json()
    # z should be approximately 3.27
    assert 2.5 < data["z_score"] < 4.0
