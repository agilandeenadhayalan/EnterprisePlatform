"""
Tests for the SLO Tracker service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_slos(client: AsyncClient):
    resp = await client.get("/slos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["slos"]) == 5


@pytest.mark.anyio
async def test_create_slo(client: AsyncClient):
    payload = {
        "service_name": "search-service",
        "slo_type": "availability",
        "target_percentage": 99.5,
        "window_days": 30,
        "description": "Search service availability",
    }
    resp = await client.post("/slos", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["service_name"] == "search-service"
    assert data["target_percentage"] == 99.5


@pytest.mark.anyio
async def test_get_slo(client: AsyncClient):
    resp = await client.get("/slos/slo-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "auth-service"
    assert data["slo_type"] == "availability"
    assert data["target_percentage"] == 99.9


@pytest.mark.anyio
async def test_get_slo_not_found(client: AsyncClient):
    resp = await client.get("/slos/slo-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_duplicate_name(client: AsyncClient):
    payload = {
        "service_name": "auth-service",
        "slo_type": "availability",
        "target_percentage": 99.9,
        "description": "Duplicate",
    }
    resp = await client.post("/slos", json=payload)
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_error_budget(client: AsyncClient):
    resp = await client.get("/slos/slo-001/budget")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slo_id"] == "slo-001"
    assert data["target"] == 99.9
    assert "error_budget_remaining" in data
    assert "burn_rate" in data
    assert isinstance(data["is_budget_exhausted"], bool)


@pytest.mark.anyio
async def test_error_budget_calculation(client: AsyncClient):
    resp = await client.get("/slos/slo-002/budget")
    assert resp.status_code == 200
    data = resp.json()
    # payment-service target is 99.0%, latest actual should be around 99.1%
    assert data["target"] == 99.0
    assert data["current_percentage"] >= 99.0
    assert data["error_budget_total"] == 1.0
    assert data["error_budget_remaining"] >= 0


@pytest.mark.anyio
async def test_compliance_history(client: AsyncClient):
    resp = await client.get("/slos/slo-001/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["records"]) == 4


@pytest.mark.anyio
async def test_record_measurement(client: AsyncClient):
    payload = {"good_events": 9990, "total_events": 10000}
    resp = await client.post("/slos/slo-001/record", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["slo_id"] == "slo-001"
    assert data["good_events"] == 9990
    assert data["total_events"] == 10000
    assert data["actual_percentage"] == 99.9


@pytest.mark.anyio
async def test_record_updates_budget(client: AsyncClient):
    # Record a poor measurement
    payload = {"good_events": 9950, "total_events": 10000}
    await client.post("/slos/slo-001/record", json=payload)
    # Check budget is impacted
    resp = await client.get("/slos/slo-001/budget")
    data = resp.json()
    assert data["current_percentage"] == 99.5
    # With 99.9% target and 99.5% actual, budget should be consumed
    assert data["error_budget_consumed_percent"] > 100


@pytest.mark.anyio
async def test_burn_rate_alerts(client: AsyncClient):
    resp = await client.get("/slos/slo-001/burn-rate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["alerts"][0]["burn_rate"] == 2.5


@pytest.mark.anyio
async def test_burn_rate_critical(client: AsyncClient):
    resp = await client.get("/slos/slo-003/burn-rate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["alerts"][0]["is_critical"] is True
    assert data["alerts"][0]["burn_rate"] == 3.0


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/slos/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_slos"] == 5
    assert "by_type" in data
    assert data["by_type"]["availability"] == 2


@pytest.mark.anyio
async def test_stats_compliance(client: AsyncClient):
    resp = await client.get("/slos/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slos_meeting_target"] >= 0
    assert data["slos_at_risk"] >= 0
    assert data["avg_error_budget_remaining"] >= 0


@pytest.mark.anyio
async def test_create_then_list(client: AsyncClient):
    payload = {
        "service_name": "new-service",
        "slo_type": "availability",
        "target_percentage": 99.0,
    }
    await client.post("/slos", json=payload)
    resp = await client.get("/slos")
    assert resp.json()["total"] == 6


@pytest.mark.anyio
async def test_history_sorted(client: AsyncClient):
    resp = await client.get("/slos/slo-001/history")
    assert resp.status_code == 200
    records = resp.json()["records"]
    # Verify records are sorted by period_start
    starts = [r["period_start"] for r in records]
    assert starts == sorted(starts)
