"""
Driver Document Service — FastAPI application.

ROUTES:
  POST  /documents                  — Upload a new document
  GET   /drivers/{id}/documents     — List documents for a driver
  GET   /documents/{id}             — Get document by ID
  PATCH /documents/{id}/verify      — Verify or reject a document
  GET   /health                     — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found

import config as service_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(service_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Driver Document Service",
    version="0.1.0",
    description="Driver document upload and verification",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/documents", response_model=schemas.DocumentResponse, status_code=201)
async def upload_document(
    body: schemas.DocumentCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Upload a new document for a driver."""
    repo = repository.DocumentRepository(db)
    doc = await repo.create_document(**body.model_dump())
    return _document_response(doc)


@app.get("/drivers/{driver_id}/documents", response_model=schemas.DocumentListResponse)
async def list_documents(
    driver_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List documents for a driver."""
    repo = repository.DocumentRepository(db)
    docs = await repo.get_driver_documents(driver_id, skip=skip, limit=limit)
    total = await repo.count_driver_documents(driver_id)
    return schemas.DocumentListResponse(
        documents=[_document_response(d) for d in docs],
        total=total,
    )


@app.get("/documents/{document_id}", response_model=schemas.DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a document by ID."""
    repo = repository.DocumentRepository(db)
    doc = await repo.get_document_by_id(document_id)
    if not doc:
        raise not_found("Document", document_id)
    return _document_response(doc)


@app.patch("/documents/{document_id}/verify", response_model=schemas.DocumentResponse)
async def verify_document(
    document_id: str,
    body: schemas.DocumentVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify or reject a document."""
    repo = repository.DocumentRepository(db)
    existing = await repo.get_document_by_id(document_id)
    if not existing:
        raise not_found("Document", document_id)

    doc = await repo.verify_document(
        document_id,
        status=body.status,
        verified_by=body.verified_by,
        rejection_reason=body.rejection_reason,
    )
    return _document_response(doc)


def _document_response(doc) -> schemas.DocumentResponse:
    return schemas.DocumentResponse(
        id=str(doc.id),
        driver_id=str(doc.driver_id),
        document_type=doc.document_type,
        document_number=doc.document_number,
        file_url=doc.file_url,
        status=doc.status,
        verified_by=str(doc.verified_by) if doc.verified_by else None,
        verified_at=doc.verified_at,
        rejection_reason=doc.rejection_reason,
        expires_at=doc.expires_at,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=service_config.settings.service_port, reload=service_config.settings.debug)
