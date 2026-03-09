"""
Tests for the Experiment Tracker API.

Covers: experiment CRUD, run logging, metric comparison, run details, edge cases.
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
async def test_list_experiments(client: AsyncClient):
    """List all experiments returns seeded data."""
    resp = await client.get("/experiments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["experiments"]) == 3


@pytest.mark.anyio
async def test_list_experiments_names(client: AsyncClient):
    """Seeded experiments have expected names."""
    resp = await client.get("/experiments")
    names = [e["name"] for e in resp.json()["experiments"]]
    assert "fare_prediction" in names
    assert "demand_forecast" in names
    assert "eta_estimation" in names


@pytest.mark.anyio
async def test_get_experiment(client: AsyncClient):
    """Get a specific experiment by ID."""
    resp = await client.get("/experiments/exp-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "exp-001"
    assert data["name"] == "fare_prediction"


@pytest.mark.anyio
async def test_get_experiment_not_found(client: AsyncClient):
    """Requesting a nonexistent experiment returns 404."""
    resp = await client.get("/experiments/exp-nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_experiment(client: AsyncClient):
    """Create a new experiment."""
    body = {
        "name": "surge_pricing_v2",
        "description": "Surge pricing model experiments",
    }
    resp = await client.post("/experiments", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "surge_pricing_v2"
    assert data["description"] == "Surge pricing model experiments"


@pytest.mark.anyio
async def test_create_experiment_appears_in_list(client: AsyncClient):
    """Newly created experiment appears in the list."""
    body = {"name": "test_experiment", "description": "Test"}
    await client.post("/experiments", json=body)
    resp = await client.get("/experiments")
    assert resp.json()["total"] == 4


@pytest.mark.anyio
async def test_list_runs_fare_prediction(client: AsyncClient):
    """Fare prediction experiment has 4 runs."""
    resp = await client.get("/experiments/exp-001/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["runs"]) == 4


@pytest.mark.anyio
async def test_list_runs_eta_estimation(client: AsyncClient):
    """ETA estimation experiment has 5 runs."""
    resp = await client.get("/experiments/exp-003/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5


@pytest.mark.anyio
async def test_list_runs_not_found(client: AsyncClient):
    """Runs for nonexistent experiment returns 404."""
    resp = await client.get("/experiments/exp-nonexistent/runs")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_run_has_params_and_metrics(client: AsyncClient):
    """Each run has params and metrics."""
    resp = await client.get("/experiments/exp-001/runs")
    run = resp.json()["runs"][0]
    assert "params" in run
    assert "metrics" in run
    assert "rmse" in run["metrics"]
    assert "artifacts" in run


@pytest.mark.anyio
async def test_create_run(client: AsyncClient):
    """Log a new run in an experiment."""
    body = {
        "run_name": "new_model_v3",
        "params": {"model": "xgboost", "n_estimators": 300},
        "metrics": {"rmse": 2.1, "mae": 1.3},
        "artifacts": ["models/new_v3.pkl"],
        "status": "completed",
    }
    resp = await client.post("/experiments/exp-001/runs", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["run_name"] == "new_model_v3"
    assert data["experiment_id"] == "exp-001"
    assert data["metrics"]["rmse"] == 2.1


@pytest.mark.anyio
async def test_create_run_appears_in_list(client: AsyncClient):
    """Newly created run appears in the runs list."""
    body = {
        "run_name": "test_run",
        "params": {},
        "metrics": {"rmse": 5.0},
        "artifacts": [],
        "status": "completed",
    }
    await client.post("/experiments/exp-002/runs", json=body)
    resp = await client.get("/experiments/exp-002/runs")
    assert resp.json()["total"] == 4


@pytest.mark.anyio
async def test_create_run_experiment_not_found(client: AsyncClient):
    """Creating a run in nonexistent experiment returns 404."""
    body = {
        "run_name": "orphan_run",
        "params": {},
        "metrics": {},
        "artifacts": [],
        "status": "completed",
    }
    resp = await client.post("/experiments/exp-nonexistent/runs", json=body)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_run_by_id(client: AsyncClient):
    """Get a specific run by its ID."""
    resp = await client.get("/runs/run-001-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "run-001-01"
    assert data["experiment_id"] == "exp-001"
    assert data["run_name"] == "rf_baseline"


@pytest.mark.anyio
async def test_get_run_not_found(client: AsyncClient):
    """Requesting a nonexistent run returns 404."""
    resp = await client.get("/runs/run-nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_compare_metrics(client: AsyncClient):
    """Compare metrics across runs in an experiment."""
    resp = await client.get("/experiments/exp-001/compare")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "exp-001"
    assert len(data["comparisons"]) > 0
    metric_names = [c["metric_name"] for c in data["comparisons"]]
    assert "rmse" in metric_names
    assert "mae" in metric_names


@pytest.mark.anyio
async def test_compare_metrics_has_run_values(client: AsyncClient):
    """Each metric comparison has values from all runs."""
    resp = await client.get("/experiments/exp-001/compare")
    data = resp.json()
    rmse_comparison = next(c for c in data["comparisons"] if c["metric_name"] == "rmse")
    assert len(rmse_comparison["runs"]) == 4  # 4 runs in fare_prediction
    for entry in rmse_comparison["runs"]:
        assert "run_id" in entry
        assert "run_name" in entry
        assert "value" in entry


@pytest.mark.anyio
async def test_compare_metrics_not_found(client: AsyncClient):
    """Comparison for nonexistent experiment returns 404."""
    resp = await client.get("/experiments/exp-nonexistent/compare")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_run_has_timestamps(client: AsyncClient):
    """Runs have start and end timestamps."""
    resp = await client.get("/runs/run-001-01")
    data = resp.json()
    assert data["start_time"] is not None
    assert data["end_time"] is not None
