"""
Tests for the Cost Tracking Service API.

Covers: allocation CRUD, cost recording, summaries, per-trip economics,
        filtering, and edge cases.
"""

import pytest
from httpx import AsyncClient


SAMPLE_ALLOCATION = {
    "service_name": "trip-service",
    "resource_type": "compute",
    "cost_per_unit": 0.002,
    "unit": "request",
    "tags": {"env": "production"},
    "period": "monthly",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_allocation(client: AsyncClient):
    """Create a cost allocation rule."""
    resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    assert resp.status_code == 201
    data = resp.json()
    assert data["service_name"] == "trip-service"
    assert data["cost_per_unit"] == 0.002
    assert "id" in data


@pytest.mark.anyio
async def test_list_allocations(client: AsyncClient):
    """List all allocations."""
    await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    await client.post("/costs/allocations", json={
        **SAMPLE_ALLOCATION, "resource_type": "storage", "cost_per_unit": 0.01,
    })

    resp = await client.get("/costs/allocations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_allocation(client: AsyncClient):
    """Get allocation details."""
    create_resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    alloc_id = create_resp.json()["id"]

    resp = await client.get(f"/costs/allocations/{alloc_id}")
    assert resp.status_code == 200
    assert resp.json()["service_name"] == "trip-service"


@pytest.mark.anyio
async def test_get_allocation_not_found(client: AsyncClient):
    """Getting non-existent allocation returns 404."""
    resp = await client.get("/costs/allocations/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_record_cost(client: AsyncClient):
    """Record a cost event."""
    alloc_resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    alloc_id = alloc_resp.json()["id"]

    resp = await client.post("/costs/record", json={
        "allocation_id": alloc_id,
        "quantity": 1000,
        "trip_id": "trip-001",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_cost"] == 2.0  # 0.002 * 1000
    assert data["trip_id"] == "trip-001"


@pytest.mark.anyio
async def test_record_cost_invalid_allocation(client: AsyncClient):
    """Recording cost with invalid allocation returns 404."""
    resp = await client.post("/costs/record", json={
        "allocation_id": "nonexistent",
        "quantity": 100,
    })
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_records(client: AsyncClient):
    """List cost records."""
    alloc_resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    alloc_id = alloc_resp.json()["id"]

    await client.post("/costs/record", json={"allocation_id": alloc_id, "quantity": 100})
    await client.post("/costs/record", json={"allocation_id": alloc_id, "quantity": 200})

    resp = await client.get("/costs/records")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_list_records_filter_by_service(client: AsyncClient):
    """Filter records by service."""
    alloc1_resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    alloc2_resp = await client.post("/costs/allocations", json={
        **SAMPLE_ALLOCATION, "service_name": "payment-service",
    })

    await client.post("/costs/record", json={"allocation_id": alloc1_resp.json()["id"], "quantity": 100})
    await client.post("/costs/record", json={"allocation_id": alloc2_resp.json()["id"], "quantity": 50})

    resp = await client.get("/costs/records?service=trip-service")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.anyio
async def test_summary(client: AsyncClient):
    """Cost summary by service/resource."""
    alloc_resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    alloc_id = alloc_resp.json()["id"]

    await client.post("/costs/record", json={"allocation_id": alloc_id, "quantity": 500})
    await client.post("/costs/record", json={"allocation_id": alloc_id, "quantity": 300})

    resp = await client.get("/costs/summary")
    assert resp.status_code == 200
    summaries = resp.json()
    assert len(summaries) == 1
    assert summaries[0]["service_name"] == "trip-service"
    assert summaries[0]["total_cost"] == 1.6  # (500+300) * 0.002


@pytest.mark.anyio
async def test_summary_empty(client: AsyncClient):
    """Summary with no records returns empty."""
    resp = await client.get("/costs/summary")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_per_trip_cost(client: AsyncClient):
    """Unit economics — cost per trip."""
    alloc_resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    alloc_id = alloc_resp.json()["id"]

    await client.post("/costs/record", json={
        "allocation_id": alloc_id, "quantity": 1000, "trip_id": "trip-001",
    })
    await client.post("/costs/record", json={
        "allocation_id": alloc_id, "quantity": 500, "trip_id": "trip-002",
    })

    resp = await client.get("/costs/per-trip")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trips"] == 2
    assert data["total_cost"] == 3.0  # (1000+500) * 0.002
    assert data["cost_per_trip"] == 1.5


@pytest.mark.anyio
async def test_per_trip_cost_no_trips(client: AsyncClient):
    """Per-trip cost with no trip records."""
    resp = await client.get("/costs/per-trip")
    assert resp.status_code == 200
    assert resp.json()["total_trips"] == 0
    assert resp.json()["cost_per_trip"] == 0.0


@pytest.mark.anyio
async def test_per_trip_cost_excludes_non_trip(client: AsyncClient):
    """Per-trip cost only includes records with trip_id."""
    alloc_resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    alloc_id = alloc_resp.json()["id"]

    await client.post("/costs/record", json={
        "allocation_id": alloc_id, "quantity": 1000, "trip_id": "trip-001",
    })
    await client.post("/costs/record", json={
        "allocation_id": alloc_id, "quantity": 500, "request_id": "req-001",
    })

    resp = await client.get("/costs/per-trip")
    assert resp.json()["total_trips"] == 1
    assert resp.json()["total_cost"] == 2.0


@pytest.mark.anyio
async def test_allocation_with_tags(client: AsyncClient):
    """Create allocation with tags."""
    resp = await client.post("/costs/allocations", json={
        **SAMPLE_ALLOCATION, "tags": {"env": "staging", "team": "platform"},
    })
    assert resp.status_code == 201
    assert resp.json()["tags"]["team"] == "platform"


@pytest.mark.anyio
async def test_summary_multiple_resources(client: AsyncClient):
    """Summary breaks down by resource type."""
    alloc1_resp = await client.post("/costs/allocations", json=SAMPLE_ALLOCATION)
    alloc2_resp = await client.post("/costs/allocations", json={
        **SAMPLE_ALLOCATION, "resource_type": "database", "cost_per_unit": 0.005,
    })

    await client.post("/costs/record", json={"allocation_id": alloc1_resp.json()["id"], "quantity": 100})
    await client.post("/costs/record", json={"allocation_id": alloc2_resp.json()["id"], "quantity": 100})

    resp = await client.get("/costs/summary")
    summary = resp.json()[0]
    assert "compute" in summary["breakdown_by_resource"]
    assert "database" in summary["breakdown_by_resource"]
