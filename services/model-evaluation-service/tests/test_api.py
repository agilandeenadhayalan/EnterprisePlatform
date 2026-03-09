"""
Tests for the Model Evaluation Service API.

Covers: evaluation runs, result listing, result details, model comparison,
leaderboard ranking, and error handling.
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
async def test_list_results(client: AsyncClient):
    """List all evaluation results returns seeded data."""
    resp = await client.get("/evaluation/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["results"]) == 5


@pytest.mark.anyio
async def test_list_results_ordered_newest_first(client: AsyncClient):
    """Results are ordered newest first."""
    resp = await client.get("/evaluation/results")
    data = resp.json()
    dates = [r["evaluated_at"] for r in data["results"]]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.anyio
async def test_get_result_details(client: AsyncClient):
    """Get specific evaluation result by ID."""
    resp = await client.get("/evaluation/results/eval-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "eval-001"
    assert data["model_name"] == "fare_predictor"
    assert data["model_version"] == "2.0.0"
    assert data["task_type"] == "regression"
    assert "rmse" in data["metrics"]
    assert "mae" in data["metrics"]
    assert "r2" in data["metrics"]
    assert "mape" in data["metrics"]


@pytest.mark.anyio
async def test_get_result_not_found(client: AsyncClient):
    """Getting a non-existent result returns 404."""
    resp = await client.get("/evaluation/results/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_run_evaluation(client: AsyncClient):
    """Run a new evaluation produces metrics."""
    resp = await client.post("/evaluation/run", json={
        "model_name": "fare_predictor",
        "model_version": "3.0.0",
        "dataset_id": "ds-rides-2024q2",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_name"] == "fare_predictor"
    assert data["model_version"] == "3.0.0"
    assert data["dataset_id"] == "ds-rides-2024q2"
    assert data["task_type"] == "regression"
    assert "rmse" in data["metrics"]
    assert "mae" in data["metrics"]
    assert "r2" in data["metrics"]
    assert "mape" in data["metrics"]
    assert data["metrics"]["rmse"] > 0
    assert 0 <= data["metrics"]["r2"] <= 1


@pytest.mark.anyio
async def test_run_evaluation_adds_to_list(client: AsyncClient):
    """Running an evaluation adds it to the results list."""
    await client.post("/evaluation/run", json={
        "model_name": "new_model",
        "model_version": "1.0.0",
        "dataset_id": "ds-test",
    })
    resp = await client.get("/evaluation/results")
    assert resp.json()["total"] == 6


@pytest.mark.anyio
async def test_compare_models_same_dataset(client: AsyncClient):
    """Compare two models on the same dataset."""
    resp = await client.post("/evaluation/compare", json={
        "model_a": "fare_predictor",
        "model_b": "demand_predictor",
        "dataset_id": "ds-rides-2024q1",
    })
    # fare_predictor has evals on ds-rides-2024q1 but demand_predictor does not
    # so this should return 404
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_compare_fare_predictor_versions(client: AsyncClient):
    """Compare two versions of fare_predictor on same dataset."""
    # Both eval-001 (v2.0.0) and eval-002 (v2.1.0) are for fare_predictor on ds-rides-2024q1
    # We can compare fare_predictor with itself but we need two different models
    # Let's add an eval for demand_predictor on the same dataset
    await client.post("/evaluation/run", json={
        "model_name": "demand_predictor",
        "model_version": "2.0.0",
        "dataset_id": "ds-rides-2024q1",
    })
    resp = await client.post("/evaluation/compare", json={
        "model_a": "fare_predictor",
        "model_b": "demand_predictor",
        "dataset_id": "ds-rides-2024q1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_a"] == "fare_predictor"
    assert data["model_b"] == "demand_predictor"
    assert data["winner"] in ("fare_predictor", "demand_predictor")
    assert data["improvement_pct"] >= 0
    assert "rmse" in data["metrics_a"]
    assert "rmse" in data["metrics_b"]


@pytest.mark.anyio
async def test_compare_models_not_found(client: AsyncClient):
    """Compare with a model that has no evaluations returns 404."""
    resp = await client.post("/evaluation/compare", json={
        "model_a": "nonexistent_a",
        "model_b": "nonexistent_b",
        "dataset_id": "ds-test",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_leaderboard_by_rmse(client: AsyncClient):
    """Leaderboard ranked by RMSE (lower is better)."""
    resp = await client.get("/evaluation/leaderboard?metric=rmse&task=regression")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "rmse"
    assert data["task"] == "regression"
    assert data["total"] == 3  # 3 unique models
    # Verify ascending order (lower RMSE = better)
    values = [e["metric_value"] for e in data["entries"]]
    assert values == sorted(values)


@pytest.mark.anyio
async def test_leaderboard_by_r2(client: AsyncClient):
    """Leaderboard ranked by R-squared (higher is better)."""
    resp = await client.get("/evaluation/leaderboard?metric=r2&task=regression")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "r2"
    # Verify descending order (higher R2 = better)
    values = [e["metric_value"] for e in data["entries"]]
    assert values == sorted(values, reverse=True)


@pytest.mark.anyio
async def test_leaderboard_by_mae(client: AsyncClient):
    """Leaderboard ranked by MAE."""
    resp = await client.get("/evaluation/leaderboard?metric=mae")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "mae"
    values = [e["metric_value"] for e in data["entries"]]
    assert values == sorted(values)


@pytest.mark.anyio
async def test_leaderboard_by_mape(client: AsyncClient):
    """Leaderboard ranked by MAPE."""
    resp = await client.get("/evaluation/leaderboard?metric=mape")
    assert resp.status_code == 200
    data = resp.json()
    values = [e["metric_value"] for e in data["entries"]]
    assert values == sorted(values)


@pytest.mark.anyio
async def test_leaderboard_entries_have_rank(client: AsyncClient):
    """Leaderboard entries have consecutive ranks starting at 1."""
    resp = await client.get("/evaluation/leaderboard?metric=rmse")
    data = resp.json()
    ranks = [e["rank"] for e in data["entries"]]
    assert ranks == list(range(1, len(ranks) + 1))


@pytest.mark.anyio
async def test_leaderboard_entries_have_model_info(client: AsyncClient):
    """Leaderboard entries include model name, version, and dataset."""
    resp = await client.get("/evaluation/leaderboard?metric=rmse")
    data = resp.json()
    for entry in data["entries"]:
        assert "model_name" in entry
        assert "model_version" in entry
        assert "dataset_id" in entry
        assert "metric_value" in entry


@pytest.mark.anyio
async def test_evaluation_metrics_realistic_ranges(client: AsyncClient):
    """Seeded evaluation metrics are within realistic ranges."""
    resp = await client.get("/evaluation/results/eval-002")
    data = resp.json()
    metrics = data["metrics"]
    assert 0 < metrics["rmse"] < 100
    assert 0 < metrics["mae"] < metrics["rmse"]
    assert 0 <= metrics["r2"] <= 1
    assert 0 < metrics["mape"] < 100


@pytest.mark.anyio
async def test_newer_fare_version_better_rmse(client: AsyncClient):
    """Newer fare_predictor version (2.1.0) has better RMSE than 2.0.0."""
    v2_0 = await client.get("/evaluation/results/eval-001")
    v2_1 = await client.get("/evaluation/results/eval-002")
    assert v2_1.json()["metrics"]["rmse"] < v2_0.json()["metrics"]["rmse"]
