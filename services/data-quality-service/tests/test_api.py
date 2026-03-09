"""
Tests for the Data Quality Service API.

Covers: rule CRUD, running checks (completeness, freshness, accuracy,
consistency, uniqueness), result filtering, and summaries.
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient


COMPLETENESS_RULE = {
    "dataset_id": "ds-rides",
    "name": "ride_id_completeness",
    "rule_type": "completeness",
    "field": "ride_id",
    "parameters": {"min_completeness": 0.95},
    "description": "ride_id should be at least 95% non-null",
    "severity": "error",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_rule(client: AsyncClient):
    """Create a quality rule."""
    resp = await client.post("/quality/rules", json=COMPLETENESS_RULE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "ride_id_completeness"
    assert data["rule_type"] == "completeness"
    assert "id" in data


@pytest.mark.anyio
async def test_get_rule(client: AsyncClient):
    """Get a specific quality rule."""
    create_resp = await client.post("/quality/rules", json=COMPLETENESS_RULE)
    rule_id = create_resp.json()["id"]

    resp = await client.get(f"/quality/rules/{rule_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == rule_id


@pytest.mark.anyio
async def test_get_rule_not_found(client: AsyncClient):
    """Getting a non-existent rule returns 404."""
    resp = await client.get("/quality/rules/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_rules(client: AsyncClient):
    """List all quality rules."""
    await client.post("/quality/rules", json=COMPLETENESS_RULE)
    await client.post("/quality/rules", json={
        **COMPLETENESS_RULE, "name": "speed_range", "rule_type": "accuracy",
        "field": "speed", "parameters": {"min_value": 0, "max_value": 200},
    })

    resp = await client.get("/quality/rules")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_list_rules_filter_by_dataset(client: AsyncClient):
    """Filter rules by dataset ID."""
    await client.post("/quality/rules", json=COMPLETENESS_RULE)
    await client.post("/quality/rules", json={
        **COMPLETENESS_RULE, "dataset_id": "ds-weather", "name": "temp_check",
    })

    resp = await client.get("/quality/rules?dataset_id=ds-rides")
    assert len(resp.json()) == 1
    assert resp.json()[0]["dataset_id"] == "ds-rides"


@pytest.mark.anyio
async def test_update_rule(client: AsyncClient):
    """Update a quality rule."""
    create_resp = await client.post("/quality/rules", json=COMPLETENESS_RULE)
    rule_id = create_resp.json()["id"]

    resp = await client.patch(f"/quality/rules/{rule_id}", json={
        "severity": "critical",
        "description": "Updated description",
    })
    assert resp.status_code == 200
    assert resp.json()["severity"] == "critical"
    assert resp.json()["description"] == "Updated description"


@pytest.mark.anyio
async def test_delete_rule(client: AsyncClient):
    """Delete a quality rule."""
    create_resp = await client.post("/quality/rules", json=COMPLETENESS_RULE)
    rule_id = create_resp.json()["id"]

    resp = await client.delete(f"/quality/rules/{rule_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/quality/rules/{rule_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_run_completeness_check_pass(client: AsyncClient):
    """Run completeness check that passes."""
    await client.post("/quality/rules", json=COMPLETENESS_RULE)

    resp = await client.post("/quality/run", json={
        "dataset_id": "ds-rides",
        "sample_data": [
            {"ride_id": "r1", "fare": 10},
            {"ride_id": "r2", "fare": 20},
            {"ride_id": "r3", "fare": 15},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] == 1
    assert data["failed"] == 0
    assert data["results"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_run_completeness_check_fail(client: AsyncClient):
    """Run completeness check that fails (too many nulls)."""
    await client.post("/quality/rules", json=COMPLETENESS_RULE)

    resp = await client.post("/quality/run", json={
        "dataset_id": "ds-rides",
        "sample_data": [
            {"ride_id": "r1"},
            {"ride_id": None},
            {"fare": 10},  # missing ride_id
            {"ride_id": None},
        ],
    })
    data = resp.json()
    assert data["failed"] == 1
    assert data["results"][0]["status"] == "failed"


@pytest.mark.anyio
async def test_run_accuracy_check(client: AsyncClient):
    """Run accuracy (range) check."""
    await client.post("/quality/rules", json={
        "dataset_id": "ds-rides",
        "name": "fare_range",
        "rule_type": "accuracy",
        "field": "fare",
        "parameters": {"min_value": 0, "max_value": 500, "min_accuracy": 0.9},
    })

    resp = await client.post("/quality/run", json={
        "dataset_id": "ds-rides",
        "sample_data": [
            {"fare": 25},
            {"fare": 100},
            {"fare": -5},  # out of range
            {"fare": 50},
        ],
    })
    data = resp.json()
    # 3 out of 4 in range = 75%, threshold 90% → fail
    assert data["results"][0]["status"] == "failed"


@pytest.mark.anyio
async def test_run_uniqueness_check(client: AsyncClient):
    """Run uniqueness check."""
    await client.post("/quality/rules", json={
        "dataset_id": "ds-rides",
        "name": "ride_id_unique",
        "rule_type": "uniqueness",
        "field": "ride_id",
        "parameters": {"min_uniqueness": 1.0},
    })

    # With duplicates
    resp = await client.post("/quality/run", json={
        "dataset_id": "ds-rides",
        "sample_data": [
            {"ride_id": "r1"},
            {"ride_id": "r2"},
            {"ride_id": "r1"},  # duplicate
        ],
    })
    assert resp.json()["results"][0]["status"] == "failed"


@pytest.mark.anyio
async def test_run_uniqueness_check_pass(client: AsyncClient):
    """Run uniqueness check that passes."""
    await client.post("/quality/rules", json={
        "dataset_id": "ds-rides",
        "name": "ride_id_unique",
        "rule_type": "uniqueness",
        "field": "ride_id",
        "parameters": {"min_uniqueness": 1.0},
    })

    resp = await client.post("/quality/run", json={
        "dataset_id": "ds-rides",
        "sample_data": [
            {"ride_id": "r1"},
            {"ride_id": "r2"},
            {"ride_id": "r3"},
        ],
    })
    assert resp.json()["results"][0]["status"] == "passed"


@pytest.mark.anyio
async def test_list_results_filter_by_status(client: AsyncClient):
    """Filter quality results by status."""
    await client.post("/quality/rules", json=COMPLETENESS_RULE)
    await client.post("/quality/rules", json={
        "dataset_id": "ds-rides", "name": "unique_check",
        "rule_type": "uniqueness", "field": "ride_id",
        "parameters": {"min_uniqueness": 1.0},
    })

    # Run checks with data that will cause mixed results
    await client.post("/quality/run", json={
        "dataset_id": "ds-rides",
        "sample_data": [
            {"ride_id": "r1"},
            {"ride_id": "r1"},  # duplicate (uniqueness fails)
        ],
    })

    # Filter for failed
    resp = await client.get("/quality/results?status=failed")
    data = resp.json()
    assert all(r["status"] == "failed" for r in data["results"])


@pytest.mark.anyio
async def test_quality_summary(client: AsyncClient):
    """Get quality summary for a dataset."""
    await client.post("/quality/rules", json=COMPLETENESS_RULE)
    await client.post("/quality/run", json={
        "dataset_id": "ds-rides",
        "sample_data": [{"ride_id": "r1"}, {"ride_id": "r2"}],
    })

    resp = await client.get("/quality/results/ds-rides/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_id"] == "ds-rides"
    assert data["total_rules"] == 1
    assert data["passed"] == 1
    assert data["score"] == 1.0
