"""
Tests for the Data Governance Service API.

Covers: policy CRUD, classification levels, dataset classification, and validation.
"""

import pytest
from httpx import AsyncClient


SAMPLE_POLICY = {
    "name": "PII Data Handling",
    "description": "Rules for handling personally identifiable information",
    "rules": [
        {"type": "encryption", "scope": "at_rest", "algorithm": "AES-256"},
        {"type": "access", "min_role": "data_analyst"},
    ],
    "classification": "confidential",
    "enforcement": "mandatory",
    "owner": "compliance-team",
}


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_create_policy(client: AsyncClient):
    """Create a governance policy."""
    resp = await client.post("/governance/policies", json=SAMPLE_POLICY)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "PII Data Handling"
    assert data["classification"] == "confidential"
    assert data["enforcement"] == "mandatory"
    assert len(data["rules"]) == 2
    assert "id" in data


@pytest.mark.anyio
async def test_get_policy(client: AsyncClient):
    """Get a specific governance policy."""
    create_resp = await client.post("/governance/policies", json=SAMPLE_POLICY)
    policy_id = create_resp.json()["id"]

    resp = await client.get(f"/governance/policies/{policy_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "PII Data Handling"


@pytest.mark.anyio
async def test_get_policy_not_found(client: AsyncClient):
    """Getting non-existent policy returns 404."""
    resp = await client.get("/governance/policies/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_policies(client: AsyncClient):
    """List all governance policies."""
    await client.post("/governance/policies", json=SAMPLE_POLICY)
    await client.post("/governance/policies", json={
        **SAMPLE_POLICY, "name": "Retention Policy",
    })

    resp = await client.get("/governance/policies")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_update_policy(client: AsyncClient):
    """Update a governance policy."""
    create_resp = await client.post("/governance/policies", json=SAMPLE_POLICY)
    policy_id = create_resp.json()["id"]

    resp = await client.patch(f"/governance/policies/{policy_id}", json={
        "enforcement": "advisory",
        "description": "Updated policy",
    })
    assert resp.status_code == 200
    assert resp.json()["enforcement"] == "advisory"
    assert resp.json()["description"] == "Updated policy"


@pytest.mark.anyio
async def test_delete_policy(client: AsyncClient):
    """Delete a governance policy."""
    create_resp = await client.post("/governance/policies", json=SAMPLE_POLICY)
    policy_id = create_resp.json()["id"]

    resp = await client.delete(f"/governance/policies/{policy_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/governance/policies/{policy_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_classification_levels(client: AsyncClient):
    """List all classification levels."""
    resp = await client.get("/governance/classifications")
    assert resp.status_code == 200
    levels = resp.json()
    assert len(levels) == 4
    level_names = [l["level"] for l in levels]
    assert "public" in level_names
    assert "internal" in level_names
    assert "confidential" in level_names
    assert "restricted" in level_names


@pytest.mark.anyio
async def test_classify_dataset(client: AsyncClient):
    """Classify a dataset."""
    resp = await client.post("/governance/classify/ds-user-profiles", json={
        "level": "confidential",
        "reason": "Contains user PII (email, phone, address)",
        "classified_by": "data-governance-admin",
        "pii_fields": ["email", "phone", "address"],
        "retention_days": 365,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_id"] == "ds-user-profiles"
    assert data["level"] == "confidential"
    assert "email" in data["pii_fields"]
    assert data["retention_days"] == 365


@pytest.mark.anyio
async def test_classify_dataset_invalid_level(client: AsyncClient):
    """Classifying with invalid level returns 400."""
    resp = await client.post("/governance/classify/ds-test", json={
        "level": "super_secret",
        "reason": "test",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_reclassify_dataset(client: AsyncClient):
    """Reclassifying a dataset overwrites the previous classification."""
    await client.post("/governance/classify/ds-data", json={
        "level": "internal",
        "reason": "Initial classification",
    })
    resp = await client.post("/governance/classify/ds-data", json={
        "level": "restricted",
        "reason": "Upgraded after audit discovered sensitive content",
    })
    assert resp.status_code == 200
    assert resp.json()["level"] == "restricted"
