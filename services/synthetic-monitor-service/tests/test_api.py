"""
Tests for the Synthetic Monitor service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_monitors(client: AsyncClient):
    resp = await client.get("/synthetic/monitors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["monitors"]) == 5


@pytest.mark.anyio
async def test_list_filter_type(client: AsyncClient):
    resp = await client.get("/synthetic/monitors", params={"type": "http"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for m in data["monitors"]:
        assert m["monitor_type"] == "http"


@pytest.mark.anyio
async def test_list_filter_active(client: AsyncClient):
    resp = await client.get("/synthetic/monitors", params={"is_active": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    for m in data["monitors"]:
        assert m["is_active"] is True


@pytest.mark.anyio
async def test_create_monitor(client: AsyncClient):
    payload = {
        "name": "Redis Health",
        "monitor_type": "tcp",
        "target_url": "redis:6379",
        "interval_seconds": 30,
        "timeout_seconds": 5,
    }
    resp = await client.post("/synthetic/monitors", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Redis Health"
    assert data["monitor_type"] == "tcp"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_get_monitor(client: AsyncClient):
    resp = await client.get("/synthetic/monitors/mon-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "API Gateway Health"
    assert data["monitor_type"] == "http"


@pytest.mark.anyio
async def test_get_monitor_not_found(client: AsyncClient):
    resp = await client.get("/synthetic/monitors/mon-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_run_check_http(client: AsyncClient):
    resp = await client.post("/synthetic/monitors/mon-001/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["monitor_id"] == "mon-001"
    assert data["is_success"] is True
    assert data["response_time_ms"] > 0
    assert data["status_code"] == 200


@pytest.mark.anyio
async def test_run_check_dns(client: AsyncClient):
    resp = await client.post("/synthetic/monitors/mon-003/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["monitor_id"] == "mon-003"
    assert data["is_success"] is True
    assert data["response_time_ms"] <= 50


@pytest.mark.anyio
async def test_results(client: AsyncClient):
    resp = await client.get("/synthetic/monitors/mon-001/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert len(data["results"]) == 10


@pytest.mark.anyio
async def test_results_for_monitor(client: AsyncClient):
    resp = await client.get("/synthetic/monitors/mon-003/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    for r in data["results"]:
        assert r["monitor_id"] == "mon-003"


@pytest.mark.anyio
async def test_uptime_calculation(client: AsyncClient):
    resp = await client.get("/synthetic/monitors/mon-001/uptime")
    assert resp.status_code == 200
    data = resp.json()
    assert data["monitor_id"] == "mon-001"
    assert data["total_checks"] == 10
    assert data["successful_checks"] == 8
    assert data["uptime_percentage"] == 80.0


@pytest.mark.anyio
async def test_uptime_percentiles(client: AsyncClient):
    resp = await client.get("/synthetic/monitors/mon-003/uptime")
    assert resp.status_code == 200
    data = resp.json()
    assert data["uptime_percentage"] == 100.0
    assert data["avg_response_time_ms"] > 0
    assert data["p95_response_time_ms"] > 0
    assert data["p99_response_time_ms"] > 0
    assert data["p99_response_time_ms"] >= data["p95_response_time_ms"]


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/synthetic/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_monitors"] == 5
    assert data["active_monitors"] == 4
    assert data["total_checks"] == 30
    assert data["overall_uptime_percentage"] > 0
    assert data["avg_response_time_ms"] > 0


@pytest.mark.anyio
async def test_create_then_list(client: AsyncClient):
    payload = {
        "name": "New Monitor",
        "monitor_type": "http",
        "target_url": "http://new-service:8000/health",
    }
    await client.post("/synthetic/monitors", json=payload)
    resp = await client.get("/synthetic/monitors")
    assert resp.json()["total"] == 6


@pytest.mark.anyio
async def test_run_then_results(client: AsyncClient):
    # Run a check
    await client.post("/synthetic/monitors/mon-002/run")
    # Verify results increased
    resp = await client.get("/synthetic/monitors/mon-002/results")
    data = resp.json()
    assert data["total"] == 6  # was 5, now 6
