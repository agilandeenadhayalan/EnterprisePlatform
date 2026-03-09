"""
Tests for the Model Registry Service API.

Covers: model registration, version creation, stage transitions,
production version retrieval, listing, and error handling.
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
async def test_list_models(client: AsyncClient):
    """List all registered models returns seeded models."""
    resp = await client.get("/registry/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    names = [m["name"] for m in data["models"]]
    assert "fare_predictor" in names
    assert "demand_predictor" in names
    assert "eta_predictor" in names


@pytest.mark.anyio
async def test_get_model_details(client: AsyncClient):
    """Get model details includes versions."""
    resp = await client.get("/registry/models/fare_predictor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "fare_predictor"
    assert data["model_type"] == "xgboost"
    assert data["task_type"] == "regression"
    assert data["latest_version"] == 3
    assert data["production_version"] == 3
    assert len(data["versions"]) == 3


@pytest.mark.anyio
async def test_get_model_not_found(client: AsyncClient):
    """Getting non-existent model returns 404."""
    resp = await client.get("/registry/models/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_register_model(client: AsyncClient):
    """Register a new model."""
    resp = await client.post("/registry/models", json={
        "name": "churn_predictor",
        "description": "Predicts customer churn probability",
        "model_type": "pytorch",
        "task_type": "classification",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "churn_predictor"
    assert data["model_type"] == "pytorch"
    assert data["task_type"] == "classification"
    assert data["latest_version"] is None


@pytest.mark.anyio
async def test_register_duplicate_model(client: AsyncClient):
    """Registering a duplicate model returns 409."""
    resp = await client.post("/registry/models", json={
        "name": "fare_predictor",
        "description": "Duplicate",
    })
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_register_model_appears_in_list(client: AsyncClient):
    """Newly registered model appears in the list."""
    await client.post("/registry/models", json={
        "name": "new_model",
        "description": "Test model",
    })
    resp = await client.get("/registry/models")
    assert resp.json()["total"] == 4


@pytest.mark.anyio
async def test_list_versions(client: AsyncClient):
    """List all versions of a model."""
    resp = await client.get("/registry/models/fare_predictor/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    # Versions are sorted descending (newest first)
    versions = [v["version"] for v in data["versions"]]
    assert versions == sorted(versions, reverse=True)


@pytest.mark.anyio
async def test_list_versions_not_found(client: AsyncClient):
    """List versions of non-existent model returns 404."""
    resp = await client.get("/registry/models/nonexistent/versions")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_version(client: AsyncClient):
    """Create a new version for a model."""
    resp = await client.post("/registry/models/fare_predictor/versions", json={
        "run_id": "run-fare-004",
        "metrics": {"rmse": 2.5, "mae": 1.6, "r2": 0.94},
        "hyperparameters": {"n_estimators": 400, "max_depth": 12},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == 4
    assert data["model_name"] == "fare_predictor"
    assert data["stage"] == "none"
    assert data["run_id"] == "run-fare-004"
    assert data["metrics"]["rmse"] == 2.5


@pytest.mark.anyio
async def test_create_version_not_found(client: AsyncClient):
    """Creating version for non-existent model returns 404."""
    resp = await client.post("/registry/models/nonexistent/versions", json={
        "run_id": "run-x",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_version_increments(client: AsyncClient):
    """Each new version increments the version number."""
    resp1 = await client.post("/registry/models/eta_predictor/versions", json={
        "run_id": "run-eta-002",
    })
    resp2 = await client.post("/registry/models/eta_predictor/versions", json={
        "run_id": "run-eta-003",
    })
    assert resp1.json()["version"] == 2
    assert resp2.json()["version"] == 3


@pytest.mark.anyio
async def test_stage_transition_to_staging(client: AsyncClient):
    """Transition a model version to staging."""
    resp = await client.post("/registry/models/fare_predictor/versions/1/stage", json={
        "stage": "staging",
        "reason": "Testing for promotion",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["from_stage"] == "archived"
    assert data["to_stage"] == "staging"
    assert data["reason"] == "Testing for promotion"
    assert data["version"]["stage"] == "staging"


@pytest.mark.anyio
async def test_stage_transition_to_production_demotes_current(client: AsyncClient):
    """Promoting to production demotes the current production version."""
    # Currently v3 is production. Promote v2.
    resp = await client.post("/registry/models/fare_predictor/versions/2/stage", json={
        "stage": "production",
        "reason": "Rolling back to v2",
    })
    assert resp.status_code == 200
    assert resp.json()["version"]["stage"] == "production"

    # v3 should now be archived
    versions_resp = await client.get("/registry/models/fare_predictor/versions")
    v3 = [v for v in versions_resp.json()["versions"] if v["version"] == 3][0]
    assert v3["stage"] == "archived"


@pytest.mark.anyio
async def test_stage_transition_not_found(client: AsyncClient):
    """Transitioning non-existent version returns 404."""
    resp = await client.post("/registry/models/fare_predictor/versions/99/stage", json={
        "stage": "production",
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_production_version(client: AsyncClient):
    """Get the production version of a model."""
    resp = await client.get("/registry/models/fare_predictor/production")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 3
    assert data["stage"] == "production"
    assert data["model_name"] == "fare_predictor"


@pytest.mark.anyio
async def test_get_production_version_demand(client: AsyncClient):
    """Get production version for demand_predictor."""
    resp = await client.get("/registry/models/demand_predictor/production")
    assert resp.status_code == 200
    assert resp.json()["version"] == 2


@pytest.mark.anyio
async def test_get_production_version_eta(client: AsyncClient):
    """Get production version for eta_predictor."""
    resp = await client.get("/registry/models/eta_predictor/production")
    assert resp.status_code == 200
    assert resp.json()["version"] == 1


@pytest.mark.anyio
async def test_get_production_version_no_production(client: AsyncClient):
    """Model with no production version returns 404."""
    await client.post("/registry/models", json={
        "name": "test_model",
        "description": "No versions",
    })
    resp = await client.get("/registry/models/test_model/production")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_version_has_metrics(client: AsyncClient):
    """Model versions include metrics."""
    resp = await client.get("/registry/models/fare_predictor/versions")
    data = resp.json()
    for v in data["versions"]:
        assert "rmse" in v["metrics"]
        assert "r2" in v["metrics"]


@pytest.mark.anyio
async def test_version_has_hyperparameters(client: AsyncClient):
    """Model versions include hyperparameters."""
    resp = await client.get("/registry/models/fare_predictor/versions")
    data = resp.json()
    for v in data["versions"]:
        assert "n_estimators" in v["hyperparameters"]
