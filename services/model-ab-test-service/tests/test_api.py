"""
Tests for the Model A/B Test Service API.

Covers: test creation, routing, outcome recording, significance testing,
test conclusion, listing, filtering, and error handling.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_list_tests(client: AsyncClient):
    """List all A/B tests returns seeded tests."""
    resp = await client.get("/ab-tests")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.anyio
async def test_list_tests_filter_active(client: AsyncClient):
    """Filter tests by active status."""
    resp = await client.get("/ab-tests?status=active")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["tests"][0]["status"] == "active"


@pytest.mark.anyio
async def test_list_tests_filter_concluded(client: AsyncClient):
    """Filter tests by concluded status."""
    resp = await client.get("/ab-tests?status=concluded")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["tests"][0]["status"] == "concluded"


@pytest.mark.anyio
async def test_get_test_details(client: AsyncClient):
    """Get A/B test details includes variant metrics."""
    resp = await client.get("/ab-tests/ab-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "ab-001"
    assert data["status"] == "active"
    assert data["champion"]["request_count"] == 150
    assert data["challenger"]["request_count"] == 120
    assert data["champion"]["model_name"] == "fare_predictor_v2.0"
    assert data["challenger"]["model_name"] == "fare_predictor_v2.1"


@pytest.mark.anyio
async def test_get_test_not_found(client: AsyncClient):
    """Getting non-existent test returns 404."""
    resp = await client.get("/ab-tests/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_test(client: AsyncClient):
    """Create a new A/B test."""
    resp = await client.post("/ab-tests", json={
        "name": "Demand Model v2 vs v1",
        "champion_model": "demand_v1",
        "challenger_model": "demand_v2",
        "traffic_split": 0.2,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Demand Model v2 vs v1"
    assert data["champion_model"] == "demand_v1"
    assert data["challenger_model"] == "demand_v2"
    assert data["traffic_split"] == 0.2
    assert data["status"] == "active"
    assert data["champion"]["traffic_pct"] == 0.8
    assert data["challenger"]["traffic_pct"] == 0.2


@pytest.mark.anyio
async def test_create_test_default_split(client: AsyncClient):
    """Create test with default 50/50 traffic split."""
    resp = await client.post("/ab-tests", json={
        "name": "Even Split Test",
        "champion_model": "model_a",
        "challenger_model": "model_b",
    })
    assert resp.status_code == 201
    assert resp.json()["traffic_split"] == 0.5


@pytest.mark.anyio
async def test_create_test_appears_in_list(client: AsyncClient):
    """Newly created test appears in list."""
    await client.post("/ab-tests", json={
        "name": "New Test",
        "champion_model": "m1",
        "challenger_model": "m2",
    })
    resp = await client.get("/ab-tests")
    assert resp.json()["total"] == 3


@pytest.mark.anyio
async def test_route_request_deterministic(client: AsyncClient):
    """Same request_id always routes to the same variant."""
    resp1 = await client.post("/ab-tests/ab-001/route", json={"request_id": "req-abc-123"})
    resp2 = await client.post("/ab-tests/ab-001/route", json={"request_id": "req-abc-123"})
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["variant"] == resp2.json()["variant"]
    assert resp1.json()["model_name"] == resp2.json()["model_name"]


@pytest.mark.anyio
async def test_route_request_returns_variant_info(client: AsyncClient):
    """Routing returns variant name, model name, and test ID."""
    resp = await client.post("/ab-tests/ab-001/route", json={"request_id": "test-req-1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["variant"] in ("champion", "challenger")
    assert data["model_name"] in ("fare_predictor_v2.0", "fare_predictor_v2.1")
    assert data["test_id"] == "ab-001"


@pytest.mark.anyio
async def test_route_different_requests_split_traffic(client: AsyncClient):
    """Different request IDs split traffic between variants."""
    variants = set()
    for i in range(50):
        resp = await client.post("/ab-tests/ab-001/route", json={"request_id": f"req-{i}"})
        variants.add(resp.json()["variant"])
    # With 50 requests and 30% challenger split, we should see both variants
    assert "champion" in variants
    assert "challenger" in variants


@pytest.mark.anyio
async def test_route_concluded_test_fails(client: AsyncClient):
    """Routing on a concluded test returns 404."""
    resp = await client.post("/ab-tests/ab-002/route", json={"request_id": "test-req"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_record_outcome_champion(client: AsyncClient):
    """Record outcome for champion variant."""
    initial = await client.get("/ab-tests/ab-001")
    initial_count = initial.json()["champion"]["request_count"]
    resp = await client.post("/ab-tests/ab-001/record", json={
        "variant": "champion",
        "value": 28.50,
    })
    assert resp.status_code == 200
    assert resp.json()["champion"]["request_count"] == initial_count + 1


@pytest.mark.anyio
async def test_record_outcome_challenger(client: AsyncClient):
    """Record outcome for challenger variant."""
    initial = await client.get("/ab-tests/ab-001")
    initial_count = initial.json()["challenger"]["request_count"]
    resp = await client.post("/ab-tests/ab-001/record", json={
        "variant": "challenger",
        "value": 30.00,
    })
    assert resp.status_code == 200
    assert resp.json()["challenger"]["request_count"] == initial_count + 1


@pytest.mark.anyio
async def test_record_outcome_not_found(client: AsyncClient):
    """Recording outcome for non-existent test returns 404."""
    resp = await client.post("/ab-tests/nonexistent/record", json={
        "variant": "champion",
        "value": 10.0,
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_significance_active_test(client: AsyncClient):
    """Significance check on active test with enough data."""
    resp = await client.get("/ab-tests/ab-001/significance")
    assert resp.status_code == 200
    data = resp.json()
    assert "p_value" in data
    assert "is_significant" in data
    assert "recommended_action" in data
    assert 0 <= data["p_value"] <= 1


@pytest.mark.anyio
async def test_significance_concluded_test(client: AsyncClient):
    """Significance check on concluded test works."""
    resp = await client.get("/ab-tests/ab-002/significance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["p_value"] < 1.0


@pytest.mark.anyio
async def test_significance_new_test_insufficient_data(client: AsyncClient):
    """Significance on test with no data returns not significant."""
    await client.post("/ab-tests", json={
        "name": "New Test",
        "champion_model": "m1",
        "challenger_model": "m2",
    })
    # Get the new test
    resp = await client.get("/ab-tests")
    new_test = [t for t in resp.json()["tests"] if t["name"] == "New Test"][0]
    sig = await client.get(f"/ab-tests/{new_test['id']}/significance")
    assert sig.status_code == 200
    assert sig.json()["is_significant"] is False
    assert sig.json()["p_value"] == 1.0


@pytest.mark.anyio
async def test_conclude_active_test(client: AsyncClient):
    """Conclude an active test declares a winner."""
    resp = await client.post("/ab-tests/ab-001/conclude")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "concluded"
    assert data["winner"] in ("champion", "challenger")
    assert data["concluded_at"] is not None


@pytest.mark.anyio
async def test_conclude_already_concluded(client: AsyncClient):
    """Concluding an already concluded test returns 404."""
    resp = await client.post("/ab-tests/ab-002/conclude")
    assert resp.status_code == 404
