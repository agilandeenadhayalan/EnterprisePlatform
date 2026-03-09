"""
Tests for the Retraining Trigger Service API.

Covers: trigger CRUD, evaluation logic, manual firing, cooldown enforcement,
history, edge cases.
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
async def test_list_triggers(client: AsyncClient):
    """List all triggers returns seeded data."""
    resp = await client.get("/triggers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["triggers"]) == 4


@pytest.mark.anyio
async def test_list_triggers_types(client: AsyncClient):
    """Seeded triggers include drift, performance, and scheduled types."""
    resp = await client.get("/triggers")
    types = [t["trigger_type"] for t in resp.json()["triggers"]]
    assert "drift" in types
    assert "performance" in types
    assert "scheduled" in types


@pytest.mark.anyio
async def test_get_trigger(client: AsyncClient):
    """Get a specific trigger by ID."""
    resp = await client.get("/triggers/trig-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "trig-001"
    assert data["model_name"] == "fare_predictor_nn"
    assert data["trigger_type"] == "drift"
    assert data["threshold"] == 0.2


@pytest.mark.anyio
async def test_get_trigger_not_found(client: AsyncClient):
    """Requesting a nonexistent trigger returns 404."""
    resp = await client.get("/triggers/trig-nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_trigger_has_cooldown(client: AsyncClient):
    """Trigger includes cooldown hours."""
    resp = await client.get("/triggers/trig-001")
    data = resp.json()
    assert data["cooldown_hours"] == 24


@pytest.mark.anyio
async def test_create_trigger(client: AsyncClient):
    """Create a new retraining trigger."""
    body = {
        "model_name": "surge_model",
        "trigger_type": "drift",
        "condition": "psi > threshold",
        "threshold": 0.25,
        "cooldown_hours": 48,
        "is_active": True,
    }
    resp = await client.post("/triggers", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_name"] == "surge_model"
    assert data["trigger_type"] == "drift"
    assert data["threshold"] == 0.25
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_create_trigger_appears_in_list(client: AsyncClient):
    """Newly created trigger appears in the list."""
    body = {
        "model_name": "test_model",
        "trigger_type": "performance",
        "condition": "mae > threshold",
        "threshold": 3.0,
        "cooldown_hours": 12,
        "is_active": True,
    }
    await client.post("/triggers", json=body)
    resp = await client.get("/triggers")
    assert resp.json()["total"] == 5


@pytest.mark.anyio
async def test_evaluate_triggers(client: AsyncClient):
    """Evaluate all triggers returns evaluations for each trigger."""
    resp = await client.post("/triggers/evaluate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4  # 4 triggers
    assert len(data["evaluations"]) == 4
    assert "fired_count" in data


@pytest.mark.anyio
async def test_evaluate_triggers_inactive_not_fired(client: AsyncClient):
    """Inactive triggers do not fire during evaluation."""
    resp = await client.post("/triggers/evaluate")
    data = resp.json()
    # trig-004 is inactive
    trig004_eval = next(e for e in data["evaluations"] if e["trigger_id"] == "trig-004")
    assert trig004_eval["fired"] is False
    assert "inactive" in trig004_eval["reason"].lower()


@pytest.mark.anyio
async def test_evaluate_triggers_has_metric_value(client: AsyncClient):
    """Each evaluation includes metric value and threshold."""
    resp = await client.post("/triggers/evaluate")
    data = resp.json()
    for ev in data["evaluations"]:
        assert "metric_value" in ev
        assert "threshold" in ev
        assert "reason" in ev


@pytest.mark.anyio
async def test_fire_trigger_manually(client: AsyncClient):
    """Manually fire a trigger records history."""
    resp = await client.post("/triggers/trig-002/fire")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trigger_id"] == "trig-002"
    assert data["model_name"] == "demand_predictor_gb"
    assert "manually fired" in data["reason"].lower()


@pytest.mark.anyio
async def test_fire_trigger_not_found(client: AsyncClient):
    """Firing a nonexistent trigger returns 404."""
    resp = await client.post("/triggers/trig-nonexistent/fire")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_fire_trigger_updates_last_fired(client: AsyncClient):
    """Manually firing updates the trigger's last_fired_at."""
    await client.post("/triggers/trig-002/fire")
    resp = await client.get("/triggers/trig-002")
    data = resp.json()
    assert data["last_fired_at"] is not None


@pytest.mark.anyio
async def test_trigger_history(client: AsyncClient):
    """Trigger history returns seeded entries."""
    resp = await client.get("/triggers/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["history"]) == 6


@pytest.mark.anyio
async def test_trigger_history_has_reasons(client: AsyncClient):
    """Each history entry has a reason."""
    resp = await client.get("/triggers/history")
    data = resp.json()
    for entry in data["history"]:
        assert "trigger_id" in entry
        assert "model_name" in entry
        assert "fired_at" in entry
        assert len(entry["reason"]) > 0


@pytest.mark.anyio
async def test_fire_trigger_adds_to_history(client: AsyncClient):
    """Manually firing a trigger adds an entry to history."""
    await client.post("/triggers/trig-001/fire")
    resp = await client.get("/triggers/history")
    data = resp.json()
    assert data["total"] == 7  # 6 seeded + 1 manual


@pytest.mark.anyio
async def test_inactive_trigger_details(client: AsyncClient):
    """Inactive trigger has is_active=False."""
    resp = await client.get("/triggers/trig-004")
    data = resp.json()
    assert data["is_active"] is False
    assert data["trigger_type"] == "scheduled"
