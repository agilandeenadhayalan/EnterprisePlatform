"""
Tests for the Log Aggregation service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_ingest_log(client: AsyncClient):
    payload = {
        "service_name": "test-service",
        "level": "INFO",
        "message": "Test log entry",
    }
    resp = await client.post("/logs/ingest", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["service_name"] == "test-service"
    assert data["level"] == "INFO"
    assert data["message"] == "Test log entry"


@pytest.mark.anyio
async def test_ingest_with_trace_id(client: AsyncClient):
    payload = {
        "service_name": "auth-service",
        "level": "ERROR",
        "message": "Auth failed",
        "trace_id": "trace-test-001",
        "span_id": "span-test-001",
        "fields": {"user_id": "u123"},
    }
    resp = await client.post("/logs/ingest", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["trace_id"] == "trace-test-001"
    assert data["span_id"] == "span-test-001"


@pytest.mark.anyio
async def test_query_all(client: AsyncClient):
    payload = {}
    resp = await client.post("/logs/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 30


@pytest.mark.anyio
async def test_query_filter_service(client: AsyncClient):
    payload = {"service_name": "auth-service"}
    resp = await client.post("/logs/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for e in data["entries"]:
        assert e["service_name"] == "auth-service"


@pytest.mark.anyio
async def test_query_filter_level(client: AsyncClient):
    payload = {"level": "ERROR"}
    resp = await client.post("/logs/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 7
    for e in data["entries"]:
        assert e["level"] == "ERROR"


@pytest.mark.anyio
async def test_query_filter_time_range(client: AsyncClient):
    payload = {
        "time_start": "2020-01-01T00:00:00Z",
        "time_end": "2099-12-31T23:59:59Z",
    }
    resp = await client.post("/logs/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 30


@pytest.mark.anyio
async def test_query_filter_search(client: AsyncClient):
    payload = {"search": "timeout"}
    resp = await client.post("/logs/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for e in data["entries"]:
        assert "timeout" in e["message"].lower()


@pytest.mark.anyio
async def test_query_combined_filters(client: AsyncClient):
    payload = {"level": "WARN", "search": "timeout"}
    resp = await client.post("/logs/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for e in data["entries"]:
        assert e["level"] == "WARN"
        assert "timeout" in e["message"].lower()


@pytest.mark.anyio
async def test_patterns(client: AsyncClient):
    resp = await client.get("/logs/patterns")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["patterns"]) == 3


@pytest.mark.anyio
async def test_patterns_count(client: AsyncClient):
    resp = await client.get("/logs/patterns")
    assert resp.status_code == 200
    data = resp.json()
    # First pattern has count 8
    timeout_pattern = next(p for p in data["patterns"] if "timeout" in p["pattern"].lower())
    assert timeout_pattern["count"] == 8


@pytest.mark.anyio
async def test_retention_policies(client: AsyncClient):
    resp = await client.get("/logs/retention-policies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["policies"]) == 2


@pytest.mark.anyio
async def test_create_retention_policy(client: AsyncClient):
    payload = {
        "name": "debug-short",
        "service_filter": "*",
        "level_filter": "DEBUG",
        "retention_days": 7,
    }
    resp = await client.post("/logs/retention-policies", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "debug-short"
    assert data["retention_days"] == 7


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/logs/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_entries"] == 30
    assert data["entries_with_traces"] > 0


@pytest.mark.anyio
async def test_stats_by_level(client: AsyncClient):
    resp = await client.get("/logs/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_level"]["INFO"] == 10
    assert data["by_level"]["WARN"] == 8
    assert data["by_level"]["ERROR"] == 7
    assert data["by_level"]["DEBUG"] == 5


@pytest.mark.anyio
async def test_ingest_then_query(client: AsyncClient):
    payload = {
        "service_name": "new-service",
        "level": "INFO",
        "message": "Unique ingested message XYZ123",
    }
    resp = await client.post("/logs/ingest", json=payload)
    assert resp.status_code == 201

    query_payload = {"search": "XYZ123"}
    resp = await client.post("/logs/query", json=query_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["entries"][0]["message"] == "Unique ingested message XYZ123"
