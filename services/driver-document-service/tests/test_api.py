"""
Tests for the driver document service API.

Pure unit tests — mock the repository layer, no DB needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime


@pytest.fixture
def mock_document():
    """Mock document ORM object."""
    doc = MagicMock()
    doc.id = "doc00000-0000-0000-0000-000000000001"
    doc.driver_id = "ddd00000-0000-0000-0000-000000000001"
    doc.document_type = "license"
    doc.document_number = "DL-12345"
    doc.file_url = "https://storage.example.com/docs/license.pdf"
    doc.status = "pending"
    doc.verified_by = None
    doc.verified_at = None
    doc.rejection_reason = None
    doc.expires_at = None
    doc.created_at = datetime(2024, 6, 15)
    doc.updated_at = datetime(2024, 6, 15)
    return doc


@pytest.fixture
def app():
    from main import app as _app
    from mobility_common.fastapi.database import get_db

    async def mock_get_db():
        yield AsyncMock()

    _app.dependency_overrides[get_db] = mock_get_db
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# -- Health check --

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# -- POST /documents --

@pytest.mark.asyncio
async def test_upload_document_success(client, mock_document):
    """Successfully upload a document."""
    with patch("repository.DocumentRepository.create_document", new_callable=AsyncMock, return_value=mock_document):
        resp = await client.post("/documents", json={
            "driver_id": "ddd00000-0000-0000-0000-000000000001",
            "document_type": "license",
            "document_number": "DL-12345",
            "file_url": "https://storage.example.com/docs/license.pdf",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["document_type"] == "license"
    assert data["status"] == "pending"


# -- GET /drivers/{id}/documents --

@pytest.mark.asyncio
async def test_list_documents(client, mock_document):
    """List documents for a driver."""
    with patch("repository.DocumentRepository.get_driver_documents", new_callable=AsyncMock, return_value=[mock_document]), \
         patch("repository.DocumentRepository.count_driver_documents", new_callable=AsyncMock, return_value=1):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_documents_empty(client):
    """List documents returns empty for driver with no documents."""
    with patch("repository.DocumentRepository.get_driver_documents", new_callable=AsyncMock, return_value=[]), \
         patch("repository.DocumentRepository.count_driver_documents", new_callable=AsyncMock, return_value=0):
        resp = await client.get("/drivers/ddd00000-0000-0000-0000-000000000001/documents")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# -- GET /documents/{id} --

@pytest.mark.asyncio
async def test_get_document_success(client, mock_document):
    """Get document by ID."""
    with patch("repository.DocumentRepository.get_document_by_id", new_callable=AsyncMock, return_value=mock_document):
        resp = await client.get(f"/documents/{mock_document.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(mock_document.id)


@pytest.mark.asyncio
async def test_get_document_not_found(client):
    """Get document returns 404 for nonexistent ID."""
    with patch("repository.DocumentRepository.get_document_by_id", new_callable=AsyncMock, return_value=None):
        resp = await client.get("/documents/nonexistent-id")
    assert resp.status_code == 404


# -- PATCH /documents/{id}/verify --

@pytest.mark.asyncio
async def test_verify_document_success(client, mock_document):
    """Successfully verify a document."""
    verified = MagicMock()
    for attr in ["id", "driver_id", "document_type", "document_number", "file_url",
                 "expires_at", "created_at", "updated_at"]:
        setattr(verified, attr, getattr(mock_document, attr))
    verified.status = "verified"
    verified.verified_by = "admin-001"
    verified.verified_at = datetime(2024, 6, 16)
    verified.rejection_reason = None

    with patch("repository.DocumentRepository.get_document_by_id", new_callable=AsyncMock, return_value=mock_document), \
         patch("repository.DocumentRepository.verify_document", new_callable=AsyncMock, return_value=verified):
        resp = await client.patch(f"/documents/{mock_document.id}/verify", json={
            "status": "verified",
            "verified_by": "admin-001",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"


@pytest.mark.asyncio
async def test_reject_document(client, mock_document):
    """Reject a document with reason."""
    rejected = MagicMock()
    for attr in ["id", "driver_id", "document_type", "document_number", "file_url",
                 "expires_at", "created_at", "updated_at", "verified_by", "verified_at"]:
        setattr(rejected, attr, getattr(mock_document, attr))
    rejected.status = "rejected"
    rejected.rejection_reason = "Expired document"

    with patch("repository.DocumentRepository.get_document_by_id", new_callable=AsyncMock, return_value=mock_document), \
         patch("repository.DocumentRepository.verify_document", new_callable=AsyncMock, return_value=rejected):
        resp = await client.patch(f"/documents/{mock_document.id}/verify", json={
            "status": "rejected",
            "rejection_reason": "Expired document",
        })
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_verify_document_not_found(client):
    """Verify returns 404 for nonexistent document."""
    with patch("repository.DocumentRepository.get_document_by_id", new_callable=AsyncMock, return_value=None):
        resp = await client.patch("/documents/nonexistent-id/verify", json={"status": "verified"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_invalid_status(client):
    """Reject invalid status value."""
    resp = await client.patch("/documents/some-id/verify", json={"status": "invalid"})
    assert resp.status_code == 422
