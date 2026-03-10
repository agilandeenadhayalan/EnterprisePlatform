"""
GDPR Service — FastAPI application.

GDPR data subject rights management (access, erasure, portability, rectification).

ROUTES:
  GET    /gdpr/requests                     — List DSRs (filter by type, status)
  POST   /gdpr/requests                     — Submit data subject request
  GET    /gdpr/requests/{id}                — Get request details
  PATCH  /gdpr/requests/{id}                — Update request status
  POST   /gdpr/requests/{id}/process        — Process/execute the request
  GET    /gdpr/requests/{id}/audit-trail     — Get processing audit trail
  GET    /gdpr/consent/{subject_email}       — Get consent records
  POST   /gdpr/consent                       — Record consent grant/withdrawal
  GET    /health                             — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository
from models import RequestType


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="GDPR data subject rights management",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/gdpr/requests", response_model=list[schemas.DSRResponse])
async def list_requests(request_type: str | None = None, status: str | None = None):
    """List all data subject requests."""
    requests = repository.repo.list_requests(request_type=request_type, status=status)
    return [schemas.DSRResponse(**r.to_dict()) for r in requests]


@app.post("/gdpr/requests", response_model=schemas.DSRResponse, status_code=201)
async def create_request(body: schemas.DSRCreate):
    """Submit a data subject request."""
    valid_types = [t.value for t in RequestType]
    if body.request_type not in valid_types:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request type '{body.request_type}'. Must be one of: {', '.join(valid_types)}",
        )

    dsr = repository.repo.create_request(
        request_type=body.request_type,
        subject_email=body.subject_email,
        data_categories=body.data_categories,
        notes=body.notes,
    )
    return schemas.DSRResponse(**dsr.to_dict())


@app.get("/gdpr/requests/{request_id}", response_model=schemas.DSRResponse)
async def get_request(request_id: str):
    """Get a data subject request by ID."""
    dsr = repository.repo.get_request(request_id)
    if not dsr:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
    return schemas.DSRResponse(**dsr.to_dict())


@app.patch("/gdpr/requests/{request_id}", response_model=schemas.DSRResponse)
async def update_request(request_id: str, body: schemas.DSRUpdate):
    """Update a data subject request."""
    update_fields = body.model_dump(exclude_unset=True)
    dsr = repository.repo.update_request(request_id, **update_fields)
    if not dsr:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
    return schemas.DSRResponse(**dsr.to_dict())


@app.post("/gdpr/requests/{request_id}/process", response_model=schemas.DSRResponse)
async def process_request(request_id: str):
    """Process/execute a data subject request."""
    dsr = repository.repo.process_request(request_id)
    if not dsr:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
    return schemas.DSRResponse(**dsr.to_dict())


@app.get("/gdpr/requests/{request_id}/audit-trail", response_model=list[schemas.AuditEntry])
async def get_audit_trail(request_id: str):
    """Get processing audit trail for a DSR."""
    trail = repository.repo.get_audit_trail(request_id)
    if trail is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
    return [schemas.AuditEntry(**entry) for entry in trail]


@app.get("/gdpr/consent/{subject_email}", response_model=list[schemas.ConsentResponse])
async def get_consent(subject_email: str):
    """Get consent records for a data subject."""
    records = repository.repo.get_consent_records(subject_email)
    return [schemas.ConsentResponse(**r.to_dict()) for r in records]


@app.post("/gdpr/consent", response_model=schemas.ConsentResponse, status_code=201)
async def record_consent(body: schemas.ConsentCreate):
    """Record consent grant or withdrawal."""
    record = repository.repo.record_consent(
        subject_email=body.subject_email,
        purpose=body.purpose,
        granted=body.granted,
    )
    return schemas.ConsentResponse(**record.to_dict())
