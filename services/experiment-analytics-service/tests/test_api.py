"""
Tests for the Experiment Analytics service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_analyze_significant(client: AsyncClient):
    payload = {
        "experiment_id": "exp-test",
        "metric_name": "click_rate",
        "control_data": [0.1, 0.12, 0.11, 0.09, 0.1, 0.11, 0.1, 0.12, 0.09, 0.1],
        "variant_data": [0.2, 0.22, 0.21, 0.19, 0.2, 0.21, 0.2, 0.22, 0.19, 0.2],
    }
    resp = await client.post("/experiment-analytics/analyze", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["significant"] is True
    assert data["p_value"] < 0.05


@pytest.mark.anyio
async def test_analyze_not_significant(client: AsyncClient):
    payload = {
        "experiment_id": "exp-test2",
        "metric_name": "load_time",
        "control_data": [2.0, 2.1, 1.9, 2.0, 2.05, 1.95, 2.0, 2.1, 1.9, 2.0],
        "variant_data": [2.01, 2.09, 1.91, 2.0, 2.04, 1.96, 2.0, 2.1, 1.9, 2.0],
    }
    resp = await client.post("/experiment-analytics/analyze", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["significant"] is False


@pytest.mark.anyio
async def test_list_analyses(client: AsyncClient):
    resp = await client.get("/experiment-analytics/analyses")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 6
    assert len(data["analyses"]) == 6


@pytest.mark.anyio
async def test_filter_experiment(client: AsyncClient):
    resp = await client.get("/experiment-analytics/analyses", params={"experiment_id": "exp-001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for a in data["analyses"]:
        assert a["experiment_id"] == "exp-001"


@pytest.mark.anyio
async def test_get_analysis(client: AsyncClient):
    resp = await client.get("/experiment-analytics/analyses/analysis-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "exp-001"
    assert data["metric_name"] == "conversion_rate"


@pytest.mark.anyio
async def test_not_found(client: AsyncClient):
    resp = await client.get("/experiment-analytics/analyses/analysis-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_segment_analysis(client: AsyncClient):
    payload = {
        "experiment_id": "exp-001",
        "segments": {
            "new_users": {"control_mean": 0.10, "variant_mean": 0.15},
            "returning_users": {"control_mean": 0.14, "variant_mean": 0.145},
        },
    }
    resp = await client.post("/experiment-analytics/segment", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "exp-001"
    assert len(data["segments"]) == 2


@pytest.mark.anyio
async def test_segment_results(client: AsyncClient):
    payload = {
        "experiment_id": "exp-001",
        "segments": {
            "premium": {"control_mean": 50.0, "variant_mean": 60.0},
        },
    }
    resp = await client.post("/experiment-analytics/segment", json=payload)
    assert resp.status_code == 200
    segs = resp.json()["segments"]
    assert segs[0]["segment_name"] == "premium"
    assert segs[0]["lift"] > 0


@pytest.mark.anyio
async def test_list_reports(client: AsyncClient):
    resp = await client.get("/experiment-analytics/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["reports"]) == 3


@pytest.mark.anyio
async def test_get_report(client: AsyncClient):
    resp = await client.get("/experiment-analytics/reports/report-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_id"] == "exp-001"
    assert "recommendation" in data


@pytest.mark.anyio
async def test_report_not_found(client: AsyncClient):
    resp = await client.get("/experiment-analytics/reports/report-999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_stats(client: AsyncClient):
    resp = await client.get("/experiment-analytics/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_analyses"] == 6
    assert data["avg_effect_size"] > 0


@pytest.mark.anyio
async def test_stats_significant_count(client: AsyncClient):
    resp = await client.get("/experiment-analytics/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["significant_count"] == 3


@pytest.mark.anyio
async def test_analysis_has_effect_size(client: AsyncClient):
    resp = await client.get("/experiment-analytics/analyses/analysis-001")
    assert resp.status_code == 200
    data = resp.json()
    assert "effect_size" in data
    assert isinstance(data["effect_size"], float)


@pytest.mark.anyio
async def test_p_value_range(client: AsyncClient):
    resp = await client.get("/experiment-analytics/analyses")
    assert resp.status_code == 200
    for a in resp.json()["analyses"]:
        assert 0.0 <= a["p_value"] <= 1.0
