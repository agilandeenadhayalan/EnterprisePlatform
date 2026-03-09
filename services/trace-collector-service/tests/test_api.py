"""
Tests for the Trace Collector service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_submit_span(client: AsyncClient):
    payload = {
        "trace_id": "trace-new-001",
        "span_id": "span-new-001",
        "operation_name": "test_op",
        "service_name": "test-service",
        "start_time": "2026-03-10T12:00:00Z",
        "end_time": "2026-03-10T12:00:00.050Z",
        "tags": {"test": "true"},
    }
    resp = await client.post("/traces/spans", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["trace_id"] == "trace-new-001"
    assert data["service_name"] == "test-service"
    assert data["duration_ms"] == 50.0


@pytest.mark.anyio
async def test_get_trace(client: AsyncClient):
    resp = await client.get("/traces/trace-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == "trace-001"
    assert len(data["spans"]) == 3
    assert data["service_count"] == 3


@pytest.mark.anyio
async def test_get_trace_not_found(client: AsyncClient):
    resp = await client.get("/traces/trace-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_traces(client: AsyncClient):
    resp = await client.get("/traces")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["traces"]) == 5


@pytest.mark.anyio
async def test_get_spans(client: AsyncClient):
    resp = await client.get("/traces/trace-002/spans")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["spans"]) == 4


@pytest.mark.anyio
async def test_get_spans_ordered(client: AsyncClient):
    resp = await client.get("/traces/trace-002/spans")
    assert resp.status_code == 200
    data = resp.json()
    spans = data["spans"]
    # Verify spans are ordered by start_time
    for i in range(len(spans) - 1):
        assert spans[i]["start_time"] <= spans[i + 1]["start_time"]


@pytest.mark.anyio
async def test_dependencies(client: AsyncClient):
    resp = await client.get("/traces/dependencies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["dependencies"]) == 8


@pytest.mark.anyio
async def test_dependencies_edges(client: AsyncClient):
    resp = await client.get("/traces/dependencies")
    assert resp.status_code == 200
    data = resp.json()
    sources = [d["source_service"] for d in data["dependencies"]]
    assert "api-gateway" in sources
    # Check a specific edge
    gw_auth = next(d for d in data["dependencies"] if d["source_service"] == "api-gateway" and d["target_service"] == "auth-service")
    assert gw_auth["call_count"] == 15


@pytest.mark.anyio
async def test_submit_child_span(client: AsyncClient):
    payload = {
        "trace_id": "trace-001",
        "span_id": "span-new-child",
        "parent_span_id": "span-001",
        "operation_name": "child_op",
        "service_name": "child-service",
        "start_time": "2026-03-10T12:00:00Z",
        "end_time": "2026-03-10T12:00:00.020Z",
    }
    resp = await client.post("/traces/spans", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_span_id"] == "span-001"


@pytest.mark.anyio
async def test_analyze_service(client: AsyncClient):
    payload = {"service_name": "api-gateway"}
    resp = await client.post("/traces/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "api-gateway"
    assert data["span_count"] == 4
    assert data["avg_duration_ms"] > 0
    assert data["error_rate"] == 0.0


@pytest.mark.anyio
async def test_analyze_not_found(client: AsyncClient):
    payload = {"service_name": "nonexistent-service"}
    resp = await client.post("/traces/analyze", json=payload)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/traces/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_traces"] == 5
    assert data["total_spans"] == 17
    assert data["unique_services"] > 0
    assert data["avg_spans_per_trace"] > 0
    assert data["error_span_count"] == 1


@pytest.mark.anyio
async def test_submit_then_get(client: AsyncClient):
    payload = {
        "trace_id": "trace-new-full",
        "span_id": "span-root",
        "operation_name": "root_op",
        "service_name": "new-service",
        "start_time": "2026-03-10T12:00:00Z",
        "end_time": "2026-03-10T12:00:00.100Z",
    }
    resp = await client.post("/traces/spans", json=payload)
    assert resp.status_code == 201

    resp = await client.get("/traces/trace-new-full")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == "trace-new-full"
    assert len(data["spans"]) == 1


@pytest.mark.anyio
async def test_full_trace_assembly(client: AsyncClient):
    resp = await client.get("/traces/trace-004")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == "trace-004"
    assert data["service_count"] == 4
    assert data["root_span"] == "GET /api/v1/users/me"
    assert len(data["spans"]) == 4
