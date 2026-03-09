"""
Tests for the Metrics Aggregation service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_definitions(client: AsyncClient):
    resp = await client.get("/metrics/definitions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 12
    assert len(data["definitions"]) == 12


@pytest.mark.anyio
async def test_list_definitions_filter_type(client: AsyncClient):
    resp = await client.get("/metrics/definitions", params={"type": "counter"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for d in data["definitions"]:
        assert d["metric_type"] == "counter"


@pytest.mark.anyio
async def test_create_definition(client: AsyncClient):
    payload = {
        "name": "new_metric_total",
        "metric_type": "counter",
        "description": "A new test metric",
        "labels": ["service"],
        "unit": "requests",
    }
    resp = await client.post("/metrics/definitions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "new_metric_total"
    assert data["metric_type"] == "counter"


@pytest.mark.anyio
async def test_get_definition(client: AsyncClient):
    resp = await client.get("/metrics/definitions/http_requests_total")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "http_requests_total"
    assert data["metric_type"] == "counter"


@pytest.mark.anyio
async def test_get_definition_not_found(client: AsyncClient):
    resp = await client.get("/metrics/definitions/nonexistent_metric")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_duplicate(client: AsyncClient):
    payload = {
        "name": "http_requests_total",
        "metric_type": "counter",
        "description": "Duplicate",
    }
    resp = await client.post("/metrics/definitions", json=payload)
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_ingest_data_point(client: AsyncClient):
    payload = {
        "metric_name": "http_requests_total",
        "labels": {"service": "test-service", "method": "GET", "status": "200"},
        "value": 42.0,
        "timestamp": "2026-03-10T12:00:00Z",
    }
    resp = await client.post("/metrics/ingest", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["metric_name"] == "http_requests_total"
    assert data["value"] == 42.0


@pytest.mark.anyio
async def test_ingest_auto_timestamp(client: AsyncClient):
    payload = {
        "metric_name": "cpu_usage_percent",
        "labels": {"service": "auth-service"},
        "value": 75.5,
    }
    resp = await client.post("/metrics/ingest", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["timestamp"] is not None


@pytest.mark.anyio
async def test_query_by_name(client: AsyncClient):
    payload = {"metric_name": "http_requests_total"}
    resp = await client.post("/metrics/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 15
    for dp in data["data_points"]:
        assert dp["metric_name"] == "http_requests_total"


@pytest.mark.anyio
async def test_query_by_labels(client: AsyncClient):
    payload = {
        "metric_name": "http_requests_total",
        "labels": {"service": "auth-service"},
    }
    resp = await client.post("/metrics/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for dp in data["data_points"]:
        assert dp["labels"]["service"] == "auth-service"


@pytest.mark.anyio
async def test_query_by_time_range(client: AsyncClient):
    payload = {
        "metric_name": "http_requests_total",
        "time_start": "2020-01-01T00:00:00Z",
        "time_end": "2099-12-31T23:59:59Z",
    }
    resp = await client.post("/metrics/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 15


@pytest.mark.anyio
async def test_aggregate_sum(client: AsyncClient):
    payload = {"metric_name": "http_requests_total", "function": "sum"}
    resp = await client.post("/metrics/aggregate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["function"] == "sum"
    assert data["result"] > 0


@pytest.mark.anyio
async def test_aggregate_avg(client: AsyncClient):
    payload = {"metric_name": "cpu_usage_percent", "function": "avg"}
    resp = await client.post("/metrics/aggregate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["function"] == "avg"
    assert data["result"] > 0


@pytest.mark.anyio
async def test_aggregate_count(client: AsyncClient):
    payload = {"metric_name": "http_requests_total", "function": "count"}
    resp = await client.post("/metrics/aggregate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == 15.0


@pytest.mark.anyio
async def test_aggregate_percentile(client: AsyncClient):
    payload = {
        "metric_name": "http_request_duration_seconds",
        "function": "percentile",
        "percentile": 99.0,
    }
    resp = await client.post("/metrics/aggregate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["function"] == "percentile"
    assert data["result"] > 0


@pytest.mark.anyio
async def test_recording_rules(client: AsyncClient):
    resp = await client.get("/metrics/recording-rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["rules"]) == 4


@pytest.mark.anyio
async def test_create_recording_rule(client: AsyncClient):
    payload = {
        "name": "test_rule",
        "expression": "avg(test_metric)",
        "interval_seconds": 60,
        "destination_metric": "test_avg",
    }
    resp = await client.post("/metrics/recording-rules", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test_rule"


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/metrics/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_definitions"] == 12
    assert data["total_data_points"] == 50
    assert data["by_type"]["counter"] == 3
    assert data["by_type"]["gauge"] == 6
    assert data["by_type"]["histogram"] == 3
