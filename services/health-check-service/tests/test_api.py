"""
Tests for the Health Check service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_probes(client: AsyncClient):
    resp = await client.get("/health-checks/probes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert len(data["probes"]) == 10


@pytest.mark.anyio
async def test_create_probe(client: AsyncClient):
    payload = {
        "service_name": "new-service",
        "probe_type": "http",
        "endpoint": "/health",
    }
    resp = await client.post("/health-checks/probes", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["service_name"] == "new-service"
    assert data["probe_type"] == "http"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_get_probe(client: AsyncClient):
    resp = await client.get("/health-checks/probes/probe-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "auth-service"
    assert data["probe_type"] == "http"


@pytest.mark.anyio
async def test_get_probe_not_found(client: AsyncClient):
    resp = await client.get("/health-checks/probes/probe-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_run_check(client: AsyncClient):
    resp = await client.post("/health-checks/run/probe-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "auth-service"
    assert data["status"] == "healthy"
    assert data["response_time_ms"] > 0


@pytest.mark.anyio
async def test_run_check_not_found(client: AsyncClient):
    resp = await client.post("/health-checks/run/probe-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_results(client: AsyncClient):
    resp = await client.get("/health-checks/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 15
    assert len(data["results"]) == 15


@pytest.mark.anyio
async def test_results_filter_service(client: AsyncClient):
    resp = await client.get("/health-checks/results", params={"service_name": "auth-service"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for r in data["results"]:
        assert r["service_name"] == "auth-service"


@pytest.mark.anyio
async def test_results_filter_status(client: AsyncClient):
    resp = await client.get("/health-checks/results", params={"status": "unhealthy"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for r in data["results"]:
        assert r["status"] == "unhealthy"


@pytest.mark.anyio
async def test_dashboard(client: AsyncClient):
    resp = await client.get("/health-checks/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert "overall_status" in data
    assert len(data["services"]) > 0


@pytest.mark.anyio
async def test_dashboard_overall_status(client: AsyncClient):
    resp = await client.get("/health-checks/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    # We have unhealthy results, so overall should be unhealthy
    assert data["overall_status"] == "unhealthy"


@pytest.mark.anyio
async def test_dependencies(client: AsyncClient):
    resp = await client.get("/health-checks/dependencies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["nodes"]) == 5


@pytest.mark.anyio
async def test_dependencies_has_edges(client: AsyncClient):
    resp = await client.get("/health-checks/dependencies")
    assert resp.status_code == 200
    data = resp.json()
    # auth-service depends on postgres and redis
    auth_node = next(n for n in data["nodes"] if n["service_name"] == "auth-service")
    assert "postgres" in auth_node["dependencies"]
    assert "redis" in auth_node["dependencies"]


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/health-checks/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_probes"] == 10
    assert data["healthy_count"] == 10
    assert data["unhealthy_count"] == 3
    assert data["degraded_count"] == 2
    assert data["avg_response_time_ms"] > 0


@pytest.mark.anyio
async def test_create_then_list(client: AsyncClient):
    payload = {
        "service_name": "test-svc",
        "probe_type": "tcp",
        "endpoint": ":8080",
    }
    resp = await client.post("/health-checks/probes", json=payload)
    assert resp.status_code == 201

    resp = await client.get("/health-checks/probes")
    assert resp.json()["total"] == 11


@pytest.mark.anyio
async def test_run_then_results(client: AsyncClient):
    await client.post("/health-checks/run/probe-001")
    resp = await client.get("/health-checks/results")
    data = resp.json()
    # Original 15 + 1 new result
    assert data["total"] == 16
