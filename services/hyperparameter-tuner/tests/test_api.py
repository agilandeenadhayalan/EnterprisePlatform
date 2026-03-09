"""
Tests for the Hyperparameter Tuner API.

Covers: search creation, trial listing, best trial, filtering by status, edge cases.
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
async def test_list_searches(client: AsyncClient):
    """List all searches returns seeded data."""
    resp = await client.get("/tuning/searches")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["searches"]) == 2


@pytest.mark.anyio
async def test_list_searches_filter_completed(client: AsyncClient):
    """Filter searches by completed status."""
    resp = await client.get("/tuning/searches?status=completed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for s in data["searches"]:
        assert s["status"] == "completed"


@pytest.mark.anyio
async def test_list_searches_filter_pending(client: AsyncClient):
    """Filter by pending returns empty when none pending."""
    resp = await client.get("/tuning/searches?status=pending")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.anyio
async def test_get_search_grid(client: AsyncClient):
    """Get grid search details."""
    resp = await client.get("/tuning/searches/search-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "search-001"
    assert data["search_strategy"] == "grid"
    assert data["model_type"] == "fare_predictor_rf"
    assert data["status"] == "completed"
    assert data["best_trial_id"] is not None


@pytest.mark.anyio
async def test_get_search_random(client: AsyncClient):
    """Get random search details."""
    resp = await client.get("/tuning/searches/search-002")
    assert resp.status_code == 200
    data = resp.json()
    assert data["search_strategy"] == "random"
    assert data["model_type"] == "fare_predictor_nn"


@pytest.mark.anyio
async def test_get_search_not_found(client: AsyncClient):
    """Requesting a nonexistent search returns 404."""
    resp = await client.get("/tuning/searches/search-nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_search_has_param_space(client: AsyncClient):
    """Search includes parameter space definitions."""
    resp = await client.get("/tuning/searches/search-001")
    data = resp.json()
    assert len(data["param_space"]) == 3
    names = [p["param_name"] for p in data["param_space"]]
    assert "n_estimators" in names
    assert "max_depth" in names


@pytest.mark.anyio
async def test_list_grid_trials(client: AsyncClient):
    """Grid search has 6 trials."""
    resp = await client.get("/tuning/searches/search-001/trials")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["trials"]) == 6


@pytest.mark.anyio
async def test_list_random_trials(client: AsyncClient):
    """Random search has 10 trials."""
    resp = await client.get("/tuning/searches/search-002/trials")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10


@pytest.mark.anyio
async def test_trial_has_params_and_metrics(client: AsyncClient):
    """Each trial has params and metrics."""
    resp = await client.get("/tuning/searches/search-001/trials")
    data = resp.json()
    trial = data["trials"][0]
    assert "params" in trial
    assert "metrics" in trial
    assert "val_loss" in trial["metrics"]
    assert "duration_seconds" in trial


@pytest.mark.anyio
async def test_trials_not_found(client: AsyncClient):
    """Trials for nonexistent search returns 404."""
    resp = await client.get("/tuning/searches/search-nonexistent/trials")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_best_trial_grid(client: AsyncClient):
    """Get best trial from grid search."""
    resp = await client.get("/tuning/searches/search-001/best")
    assert resp.status_code == 200
    data = resp.json()
    assert data["search_id"] == "search-001"
    assert data["status"] == "completed"
    assert "val_loss" in data["metrics"]


@pytest.mark.anyio
async def test_get_best_trial_random(client: AsyncClient):
    """Get best trial from random search."""
    resp = await client.get("/tuning/searches/search-002/best")
    assert resp.status_code == 200
    data = resp.json()
    assert data["search_id"] == "search-002"


@pytest.mark.anyio
async def test_best_trial_is_actually_best(client: AsyncClient):
    """Best trial has the lowest val_loss among all trials."""
    # Get best
    best_resp = await client.get("/tuning/searches/search-001/best")
    best = best_resp.json()
    best_val = best["metrics"]["val_loss"]
    # Get all trials
    trials_resp = await client.get("/tuning/searches/search-001/trials")
    trials = trials_resp.json()["trials"]
    for trial in trials:
        assert trial["metrics"]["val_loss"] >= best_val


@pytest.mark.anyio
async def test_best_trial_not_found(client: AsyncClient):
    """Best trial for nonexistent search returns 404."""
    resp = await client.get("/tuning/searches/search-nonexistent/best")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_search(client: AsyncClient):
    """Create a new hyperparameter search."""
    body = {
        "model_type": "demand_predictor_gb",
        "search_strategy": "bayesian",
        "param_space": [
            {"param_name": "n_estimators", "type": "int", "min": 50, "max": 500},
            {"param_name": "learning_rate", "type": "float", "min": 0.001, "max": 0.1},
        ],
        "objective_metric": "val_mae",
    }
    resp = await client.post("/tuning/searches", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_type"] == "demand_predictor_gb"
    assert data["search_strategy"] == "bayesian"
    assert data["status"] == "pending"
    assert data["objective_metric"] == "val_mae"
    assert len(data["param_space"]) == 2


@pytest.mark.anyio
async def test_create_search_appears_in_list(client: AsyncClient):
    """Newly created search appears in the list."""
    body = {
        "model_type": "eta_predictor_nn",
        "search_strategy": "random",
        "param_space": [
            {"param_name": "dropout", "type": "float", "min": 0.0, "max": 0.5},
        ],
        "objective_metric": "val_loss",
    }
    await client.post("/tuning/searches", json=body)
    resp = await client.get("/tuning/searches")
    assert resp.json()["total"] == 3
