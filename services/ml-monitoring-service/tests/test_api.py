"""
Tests for the ML Monitoring service API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_drift_results(client: AsyncClient):
    resp = await client.get("/monitoring/drift/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["results"]) == 8


@pytest.mark.anyio
async def test_list_drift_results_contains_drifted(client: AsyncClient):
    resp = await client.get("/monitoring/drift/results")
    data = resp.json()
    drifted = [r for r in data["results"] if r["is_drifted"]]
    assert len(drifted) == 3


@pytest.mark.anyio
async def test_detect_drift_psi_no_drift(client: AsyncClient):
    """Same distribution should not trigger drift."""
    import random
    rng = random.Random(99)
    ref = [rng.gauss(10.0, 1.0) for _ in range(200)]
    cur = [rng.gauss(10.0, 1.0) for _ in range(200)]
    payload = {"feature_name": "test_feat", "reference_data": ref, "current_data": cur, "method": "psi"}
    resp = await client.post("/monitoring/drift/detect", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric_name"] == "psi"
    assert data["is_drifted"] is False


@pytest.mark.anyio
async def test_detect_drift_psi_with_drift(client: AsyncClient):
    """Shifted distribution should trigger drift."""
    import random
    rng = random.Random(99)
    ref = [rng.gauss(10.0, 1.0) for _ in range(200)]
    cur = [rng.gauss(15.0, 1.0) for _ in range(200)]
    payload = {"feature_name": "test_feat", "reference_data": ref, "current_data": cur, "method": "psi"}
    resp = await client.post("/monitoring/drift/detect", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_drifted"] is True
    assert data["metric_value"] > 0.2


@pytest.mark.anyio
async def test_detect_drift_ks_no_drift(client: AsyncClient):
    import random
    rng = random.Random(50)
    ref = [rng.gauss(5.0, 1.0) for _ in range(200)]
    cur = [rng.gauss(5.0, 1.0) for _ in range(200)]
    payload = {"feature_name": "ks_feat", "reference_data": ref, "current_data": cur, "method": "ks"}
    resp = await client.post("/monitoring/drift/detect", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric_name"] == "ks"
    assert data["is_drifted"] is False


@pytest.mark.anyio
async def test_detect_drift_ks_with_drift(client: AsyncClient):
    import random
    rng = random.Random(50)
    ref = [rng.gauss(5.0, 1.0) for _ in range(200)]
    cur = [rng.gauss(8.0, 1.0) for _ in range(200)]
    payload = {"feature_name": "ks_feat", "reference_data": ref, "current_data": cur, "method": "ks"}
    resp = await client.post("/monitoring/drift/detect", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_drifted"] is True
    assert data["metric_value"] > 0.15


@pytest.mark.anyio
async def test_detect_drift_jsd_no_drift(client: AsyncClient):
    import random
    rng = random.Random(77)
    ref = [rng.gauss(20.0, 2.0) for _ in range(200)]
    cur = [rng.gauss(20.0, 2.0) for _ in range(200)]
    payload = {"feature_name": "jsd_feat", "reference_data": ref, "current_data": cur, "method": "jsd"}
    resp = await client.post("/monitoring/drift/detect", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric_name"] == "jsd"
    assert data["is_drifted"] is False


@pytest.mark.anyio
async def test_detect_drift_jsd_with_drift(client: AsyncClient):
    import random
    rng = random.Random(77)
    ref = [rng.gauss(20.0, 2.0) for _ in range(200)]
    cur = [rng.gauss(30.0, 2.0) for _ in range(200)]
    payload = {"feature_name": "jsd_feat", "reference_data": ref, "current_data": cur, "method": "jsd"}
    resp = await client.post("/monitoring/drift/detect", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_drifted"] is True
    assert data["metric_value"] > 0.1


@pytest.mark.anyio
async def test_detect_drift_creates_alert(client: AsyncClient):
    """When drift is detected, an alert should be created."""
    import random
    rng = random.Random(99)
    ref = [rng.gauss(10.0, 1.0) for _ in range(200)]
    cur = [rng.gauss(20.0, 1.0) for _ in range(200)]
    payload = {"feature_name": "alert_feat", "reference_data": ref, "current_data": cur, "method": "psi"}
    resp = await client.post("/monitoring/drift/detect", json=payload)
    assert resp.json()["is_drifted"] is True

    alerts_resp = await client.get("/monitoring/alerts")
    alerts = alerts_resp.json()["alerts"]
    alert_features = [a["feature_name"] for a in alerts]
    assert "alert_feat" in alert_features


@pytest.mark.anyio
async def test_detect_drift_adds_to_results(client: AsyncClient):
    """Detection should add a new result to the results list."""
    import random
    rng = random.Random(42)
    ref = [rng.gauss(5.0, 1.0) for _ in range(100)]
    cur = [rng.gauss(5.0, 1.0) for _ in range(100)]
    payload = {"feature_name": "new_feat", "reference_data": ref, "current_data": cur, "method": "psi"}
    await client.post("/monitoring/drift/detect", json=payload)

    resp = await client.get("/monitoring/drift/results")
    assert resp.json()["total"] == 9


@pytest.mark.anyio
async def test_set_reference(client: AsyncClient):
    payload = {"feature_name": "new_feature", "values": [1.0, 2.0, 3.0, 4.0, 5.0]}
    resp = await client.post("/monitoring/drift/reference", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["feature_name"] == "new_feature"
    assert data["mean"] == 3.0
    assert len(data["values"]) == 5


@pytest.mark.anyio
async def test_set_reference_updates_existing(client: AsyncClient):
    payload = {"feature_name": "trip_distance", "values": [10.0, 20.0, 30.0]}
    resp = await client.post("/monitoring/drift/reference", json=payload)
    assert resp.status_code == 201
    assert resp.json()["mean"] == 20.0


@pytest.mark.anyio
async def test_dashboard(client: AsyncClient):
    resp = await client.get("/monitoring/drift/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_features"] == 5
    assert data["drifted_count"] >= 1
    assert len(data["features"]) == 5


@pytest.mark.anyio
async def test_dashboard_features_have_reference(client: AsyncClient):
    resp = await client.get("/monitoring/drift/dashboard")
    data = resp.json()
    for f in data["features"]:
        assert f["has_reference"] is True


@pytest.mark.anyio
async def test_concept_drift_no_drift(client: AsyncClient):
    """Stable error should not indicate concept drift."""
    preds = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    actuals = [1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1]
    payload = {"model_name": "test_model", "predictions": preds, "actuals": actuals}
    resp = await client.post("/monitoring/concept-drift", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_name"] == "test_model"
    assert data["is_drifted"] is False


@pytest.mark.anyio
async def test_concept_drift_with_drift(client: AsyncClient):
    """Increasing error trend should indicate concept drift."""
    preds = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    actuals = [1.0, 2.0, 3.0, 4.0, 5.0, 9.0, 11.0, 13.0, 15.0, 17.0]
    payload = {"model_name": "degrading_model", "predictions": preds, "actuals": actuals}
    resp = await client.post("/monitoring/concept-drift", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_drifted"] is True
    assert data["error_trend"] > 0


@pytest.mark.anyio
async def test_list_alerts(client: AsyncClient):
    resp = await client.get("/monitoring/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["alerts"]) == 3


@pytest.mark.anyio
async def test_alerts_have_correct_fields(client: AsyncClient):
    resp = await client.get("/monitoring/alerts")
    data = resp.json()
    for alert in data["alerts"]:
        assert "id" in alert
        assert "feature_name" in alert
        assert "severity" in alert
        assert "message" in alert
        assert alert["severity"] in ("low", "medium", "high")
