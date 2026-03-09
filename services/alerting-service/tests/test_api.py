"""
Tests for the Alerting service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_rules(client: AsyncClient):
    resp = await client.get("/alerts/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["rules"]) == 8


@pytest.mark.anyio
async def test_list_rules_filter_severity(client: AsyncClient):
    resp = await client.get("/alerts/rules", params={"severity": "critical"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for r in data["rules"]:
        assert r["severity"] == "critical"


@pytest.mark.anyio
async def test_list_rules_filter_active(client: AsyncClient):
    resp = await client.get("/alerts/rules", params={"is_active": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8


@pytest.mark.anyio
async def test_get_rule(client: AsyncClient):
    resp = await client.get("/alerts/rules/rule-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "CPU High"
    assert data["severity"] == "critical"


@pytest.mark.anyio
async def test_get_rule_not_found(client: AsyncClient):
    resp = await client.get("/alerts/rules/rule-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_rule(client: AsyncClient):
    payload = {
        "name": "New Test Rule",
        "severity": "warning",
        "condition_type": "threshold",
        "condition_config": {"metric": "test", "operator": ">", "value": 50},
        "channel": "slack",
    }
    resp = await client.post("/alerts/rules", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Test Rule"
    assert data["severity"] == "warning"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_fire_alert(client: AsyncClient):
    payload = {"rule_id": "rule-001", "message": "CPU at 98%"}
    resp = await client.post("/alerts/fire", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "firing"
    assert data["rule_id"] == "rule-001"


@pytest.mark.anyio
async def test_fire_alert_creates_event(client: AsyncClient):
    payload = {"rule_id": "rule-002", "message": "Error rate at 10%"}
    resp = await client.post("/alerts/fire", json=payload)
    assert resp.status_code == 201
    # Verify event in history
    hist = await client.get("/alerts/history")
    events = hist.json()["events"]
    assert any(e["message"] == "Error rate at 10%" for e in events)


@pytest.mark.anyio
async def test_resolve_alert(client: AsyncClient):
    resp = await client.post("/alerts/resolve/evt-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None


@pytest.mark.anyio
async def test_resolve_not_found(client: AsyncClient):
    resp = await client.post("/alerts/resolve/evt-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_silence_rule(client: AsyncClient):
    resp = await client.post("/alerts/silence/rule-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False


@pytest.mark.anyio
async def test_acknowledge_alert(client: AsyncClient):
    payload = {"acknowledged_by": "oncall-engineer"}
    resp = await client.post("/alerts/acknowledge/evt-001", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "acknowledged"
    assert data["acknowledged_by"] == "oncall-engineer"


@pytest.mark.anyio
async def test_history(client: AsyncClient):
    resp = await client.get("/alerts/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["events"]) == 6


@pytest.mark.anyio
async def test_history_filter_status(client: AsyncClient):
    resp = await client.get("/alerts/history", params={"status": "firing"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for e in data["events"]:
        assert e["status"] == "firing"


@pytest.mark.anyio
async def test_routing_rules(client: AsyncClient):
    resp = await client.get("/alerts/routing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["routing_rules"]) == 4


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/alerts/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rules"] == 8
    assert data["active_rules"] == 8
    assert data["firing_alerts"] == 3
    assert data["resolved_alerts"] == 2


@pytest.mark.anyio
async def test_stats_counts(client: AsyncClient):
    resp = await client.get("/alerts/stats")
    assert resp.status_code == 200
    data = resp.json()
    sev = data["by_severity"]
    assert sev["critical"] == 3
    assert sev["warning"] == 4
    assert sev["info"] == 1
