"""
Tests for the Fraud Detection service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_alerts(client: AsyncClient):
    resp = await client.get("/fraud/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["alerts"]) == 8


@pytest.mark.anyio
async def test_filter_status(client: AsyncClient):
    resp = await client.get("/fraud/alerts", params={"status": "open"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for a in data["alerts"]:
        assert a["status"] == "open"


@pytest.mark.anyio
async def test_filter_type(client: AsyncClient):
    resp = await client.get("/fraud/alerts", params={"alert_type": "velocity"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for a in data["alerts"]:
        assert a["alert_type"] == "velocity"


@pytest.mark.anyio
async def test_get_alert(client: AsyncClient):
    resp = await client.get("/fraud/alerts/alert-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["transaction_id"] == "txn-101"
    assert data["alert_type"] == "velocity"


@pytest.mark.anyio
async def test_not_found(client: AsyncClient):
    resp = await client.get("/fraud/alerts/alert-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_resolve_alert(client: AsyncClient):
    resp = await client.post("/fraud/alerts/alert-001/resolve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"


@pytest.mark.anyio
async def test_resolve_not_found(client: AsyncClient):
    resp = await client.post("/fraud/alerts/alert-999/resolve")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_score_transaction(client: AsyncClient):
    payload = {
        "transaction_id": "txn-200",
        "user_id": "user-X",
        "amount": 100.0,
        "features": {},
    }
    resp = await client.post("/fraud/score", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["transaction_id"] == "txn-200"
    assert "ensemble_score" in data
    assert "scores" in data


@pytest.mark.anyio
async def test_score_flagged(client: AsyncClient):
    payload = {
        "transaction_id": "txn-201",
        "user_id": "user-Y",
        "amount": 9000.0,
        "features": {"foreign": True},
    }
    resp = await client.post("/fraud/score", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["flagged"] is True


@pytest.mark.anyio
async def test_score_not_flagged(client: AsyncClient):
    payload = {
        "transaction_id": "txn-202",
        "user_id": "user-Z",
        "amount": 50.0,
        "features": {},
    }
    resp = await client.post("/fraud/score", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["flagged"] is False


@pytest.mark.anyio
async def test_list_rules(client: AsyncClient):
    resp = await client.get("/fraud/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["rules"]) == 6


@pytest.mark.anyio
async def test_create_rule(client: AsyncClient):
    payload = {
        "name": "new_rule",
        "rule_type": "custom",
        "threshold": 0.9,
        "config": {"key": "value"},
    }
    resp = await client.post("/fraud/rules", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "new_rule"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_toggle_rule(client: AsyncClient):
    # rule-001 is active, toggle should make inactive
    resp = await client.post("/fraud/rules/rule-001/toggle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False


@pytest.mark.anyio
async def test_toggle_not_found(client: AsyncClient):
    resp = await client.post("/fraud/rules/rule-999/toggle")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_graph_analysis(client: AsyncClient):
    payload = {"user_ids": ["user-A", "user-B", "user-C"]}
    resp = await client.post("/fraud/analyze-graph", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "suspicious_patterns" in data
    assert len(data["suspicious_patterns"]) > 0
    assert data["risk_level"] == "high"


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/fraud/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_alerts"] == 8
    assert data["avg_risk_score"] > 0


@pytest.mark.anyio
async def test_stats_by_status(client: AsyncClient):
    resp = await client.get("/fraud/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_status"]["open"] == 3
    assert data["by_status"]["resolved"] == 3
    assert data["by_status"]["investigating"] == 2


@pytest.mark.anyio
async def test_alert_risk_score_range(client: AsyncClient):
    resp = await client.get("/fraud/alerts")
    assert resp.status_code == 200
    for a in resp.json()["alerts"]:
        assert 0.0 <= a["risk_score"] <= 1.0
