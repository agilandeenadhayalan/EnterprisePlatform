"""
Tests for the Feature Freshness Monitor service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_dashboard(client: AsyncClient):
    resp = await client.get("/freshness/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_features"] == 15
    assert data["fresh_count"] == 10
    assert data["stale_count"] == 5
    assert data["freshness_percentage"] == pytest.approx(66.7, abs=0.1)


@pytest.mark.anyio
async def test_dashboard_has_violations(client: AsyncClient):
    resp = await client.get("/freshness/status")
    data = resp.json()
    assert data["critical_violations"] + data["warning_violations"] == 5


@pytest.mark.anyio
async def test_all_features(client: AsyncClient):
    resp = await client.get("/freshness/features")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 15
    assert data["fresh_count"] == 10
    assert data["stale_count"] == 5


@pytest.mark.anyio
async def test_filter_fresh_features(client: AsyncClient):
    resp = await client.get("/freshness/features", params={"is_fresh": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    for f in data["features"]:
        assert f["is_fresh"] is True


@pytest.mark.anyio
async def test_filter_stale_features(client: AsyncClient):
    resp = await client.get("/freshness/features", params={"is_fresh": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    for f in data["features"]:
        assert f["is_fresh"] is False


@pytest.mark.anyio
async def test_violations(client: AsyncClient):
    resp = await client.get("/freshness/violations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    for v in data["violations"]:
        assert v["severity"] in ("critical", "warning")
        assert v["actual_staleness"] > v["sla_seconds"]


@pytest.mark.anyio
async def test_violations_filter_critical(client: AsyncClient):
    resp = await client.get("/freshness/violations", params={"severity": "critical"})
    assert resp.status_code == 200
    for v in resp.json()["violations"]:
        assert v["severity"] == "critical"


@pytest.mark.anyio
async def test_violations_filter_warning(client: AsyncClient):
    resp = await client.get("/freshness/violations", params={"severity": "warning"})
    assert resp.status_code == 200
    for v in resp.json()["violations"]:
        assert v["severity"] == "warning"


@pytest.mark.anyio
async def test_check_run(client: AsyncClient):
    resp = await client.post("/freshness/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checked"] == 15
    assert data["fresh"] == 10
    assert data["stale"] == 5
    assert data["violations"] == 5
    assert "10/15" in data["message"]


@pytest.mark.anyio
async def test_set_sla(client: AsyncClient):
    resp = await client.post("/freshness/sla", json={
        "feature_name": "driver_avg_rating",
        "sla_seconds": 900,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature_name"] == "driver_avg_rating"
    assert data["sla_seconds"] == 900


@pytest.mark.anyio
async def test_set_sla_makes_feature_stale(client: AsyncClient):
    """Setting a very tight SLA should make a fresh feature become stale."""
    await client.post("/freshness/sla", json={
        "feature_name": "driver_avg_rating",
        "sla_seconds": 1,  # 1 second SLA — will be violated
    })
    resp = await client.get("/freshness/features", params={"is_fresh": False})
    stale_names = [f["feature_name"] for f in resp.json()["features"]]
    assert "driver_avg_rating" in stale_names


@pytest.mark.anyio
async def test_set_sla_makes_feature_fresh(client: AsyncClient):
    """Setting a very loose SLA should make a stale feature become fresh."""
    await client.post("/freshness/sla", json={
        "feature_name": "driver_cancel_rate",
        "sla_seconds": 999999,  # Very loose SLA
    })
    resp = await client.get("/freshness/features", params={"is_fresh": True})
    fresh_names = [f["feature_name"] for f in resp.json()["features"]]
    assert "driver_cancel_rate" in fresh_names


@pytest.mark.anyio
async def test_violation_severity_logic(client: AsyncClient):
    """Violations with staleness > 5x SLA should be critical."""
    resp = await client.get("/freshness/violations")
    for v in resp.json()["violations"]:
        ratio = v["actual_staleness"] / v["sla_seconds"]
        if ratio > 5:
            assert v["severity"] == "critical"
        else:
            assert v["severity"] == "warning"
