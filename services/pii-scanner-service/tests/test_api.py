"""
Tests for the PII Scanner Service API.

Covers: text scanning, dataset scanning, scan results, patterns, masking, and validation.
"""

import pytest
from httpx import AsyncClient


TEXT_WITH_PII = "Contact John at john@example.com or call 555-123-4567. SSN: 123-45-6789. Card: 4111-1111-1111-1111. Server: 192.168.1.100"


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_scan_text_with_pii(client: AsyncClient):
    """Scan text that contains PII."""
    resp = await client.post("/pii/scan", json={
        "text": TEXT_WITH_PII,
        "source": "test",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["pii_count"] >= 4  # email, phone, ssn, credit_card
    assert data["source"] == "test"
    assert "id" in data


@pytest.mark.anyio
async def test_scan_text_no_pii(client: AsyncClient):
    """Scan text with no PII returns empty findings."""
    resp = await client.post("/pii/scan", json={
        "text": "Hello world, this is a safe text with no PII.",
    })
    assert resp.status_code == 200
    assert resp.json()["pii_count"] == 0
    assert resp.json()["findings"] == []


@pytest.mark.anyio
async def test_scan_detects_email(client: AsyncClient):
    """Scanner detects email addresses."""
    resp = await client.post("/pii/scan", json={
        "text": "Email me at user@company.org please",
    })
    assert resp.status_code == 200
    findings = resp.json()["findings"]
    assert any(f["pii_type"] == "email" for f in findings)


@pytest.mark.anyio
async def test_scan_detects_ssn(client: AsyncClient):
    """Scanner detects SSN patterns."""
    resp = await client.post("/pii/scan", json={
        "text": "My SSN is 123-45-6789",
    })
    assert resp.status_code == 200
    findings = resp.json()["findings"]
    assert any(f["pii_type"] == "ssn" for f in findings)


@pytest.mark.anyio
async def test_scan_dataset(client: AsyncClient):
    """Scan a named dataset for PII."""
    resp = await client.post("/pii/scan-dataset", json={
        "dataset_name": "user_profiles",
        "sample_data": [
            "John Doe, john@example.com, 555-123-4567",
            "Jane Smith, jane@test.org, 555-987-6543",
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "user_profiles"
    assert data["pii_count"] >= 4  # 2 emails + 2 phones


@pytest.mark.anyio
async def test_list_scan_results(client: AsyncClient):
    """List past scan results."""
    await client.post("/pii/scan", json={"text": "test@example.com"})
    await client.post("/pii/scan", json={"text": "another@test.com"})

    resp = await client.get("/pii/scan-results")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.anyio
async def test_get_scan_result(client: AsyncClient):
    """Get a specific scan result."""
    scan_resp = await client.post("/pii/scan", json={"text": "user@example.com"})
    scan_id = scan_resp.json()["id"]

    resp = await client.get(f"/pii/scan-results/{scan_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == scan_id


@pytest.mark.anyio
async def test_get_scan_result_not_found(client: AsyncClient):
    """Getting non-existent scan result returns 404."""
    resp = await client.get("/pii/scan-results/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_patterns(client: AsyncClient):
    """List available PII detection patterns."""
    resp = await client.get("/pii/patterns")
    assert resp.status_code == 200
    patterns = resp.json()
    assert len(patterns) == 5
    pii_types = [p["pii_type"] for p in patterns]
    assert "ssn" in pii_types
    assert "email" in pii_types
    assert "phone" in pii_types
    assert "credit_card" in pii_types
    assert "ip_address" in pii_types


@pytest.mark.anyio
async def test_mask_redact(client: AsyncClient):
    """Mask PII with redact strategy."""
    resp = await client.post("/pii/mask", json={
        "text": "Email: user@example.com SSN: 123-45-6789",
        "strategy": "redact",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "[REDACTED]" in data["masked_text"]
    assert data["masked_count"] >= 2
    assert data["strategy"] == "redact"


@pytest.mark.anyio
async def test_mask_partial(client: AsyncClient):
    """Mask PII with partial strategy."""
    resp = await client.post("/pii/mask", json={
        "text": "SSN: 123-45-6789",
        "strategy": "partial",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["masked_count"] >= 1
    assert data["strategy"] == "partial"
    # Partial should show last 4 chars
    assert "6789" in data["masked_text"]


@pytest.mark.anyio
async def test_mask_hash(client: AsyncClient):
    """Mask PII with hash strategy."""
    resp = await client.post("/pii/mask", json={
        "text": "Email: user@example.com",
        "strategy": "hash",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["masked_count"] >= 1
    assert data["strategy"] == "hash"
    assert "user@example.com" not in data["masked_text"]


@pytest.mark.anyio
async def test_mask_invalid_strategy(client: AsyncClient):
    """Masking with invalid strategy returns 400."""
    resp = await client.post("/pii/mask", json={
        "text": "test@example.com",
        "strategy": "invalid",
    })
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_scan_finding_positions(client: AsyncClient):
    """Findings include correct start/end positions."""
    text = "Call 555-123-4567 now"
    resp = await client.post("/pii/scan", json={"text": text})
    assert resp.status_code == 200
    findings = resp.json()["findings"]
    assert len(findings) >= 1
    phone_finding = next(f for f in findings if f["pii_type"] == "phone")
    assert phone_finding["start"] >= 0
    assert phone_finding["end"] > phone_finding["start"]
    assert text[phone_finding["start"]:phone_finding["end"]] == phone_finding["value"]


@pytest.mark.anyio
async def test_mask_text_no_pii(client: AsyncClient):
    """Masking text with no PII returns original text."""
    resp = await client.post("/pii/mask", json={
        "text": "Hello world, no PII here.",
        "strategy": "redact",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["masked_count"] == 0
    assert data["masked_text"] == "Hello world, no PII here."


@pytest.mark.anyio
async def test_scan_detects_credit_card(client: AsyncClient):
    """Scanner detects credit card numbers."""
    resp = await client.post("/pii/scan", json={
        "text": "Card number is 4111-1111-1111-1111",
    })
    assert resp.status_code == 200
    findings = resp.json()["findings"]
    assert any(f["pii_type"] == "credit_card" for f in findings)
