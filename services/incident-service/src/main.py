"""
Incident Service — FastAPI application.

Incident lifecycle management — reporting, investigation, resolution.

ROUTES:
  GET    /incidents                     — List incidents (filter by status, severity)
  POST   /incidents                     — Report new incident
  GET    /incidents/{id}                — Get incident details
  PATCH  /incidents/{id}                — Update incident
  POST   /incidents/{id}/investigate    — Begin investigation
  POST   /incidents/{id}/resolve        — Resolve incident
  POST   /incidents/{id}/notes          — Add investigation note
  GET    /incidents/stats               — Incident statistics
  GET    /health                        — Health check (provided by create_app)
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
from models import IncidentSeverity


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Incident lifecycle management",
    lifespan=lifespan,
)


# ── Routes ──

# NOTE: /incidents/stats must be above /incidents/{id} to avoid path conflicts
@app.get("/incidents/stats", response_model=schemas.IncidentStatsResponse)
async def get_stats():
    """Get incident statistics."""
    stats = repository.repo.get_stats()
    return schemas.IncidentStatsResponse(**stats)


@app.get("/incidents", response_model=list[schemas.IncidentResponse])
async def list_incidents(status: str | None = None, severity: str | None = None):
    """List all incidents."""
    incidents = repository.repo.list_incidents(status=status, severity=severity)
    return [schemas.IncidentResponse(**i.to_dict()) for i in incidents]


@app.post("/incidents", response_model=schemas.IncidentResponse, status_code=201)
async def create_incident(body: schemas.IncidentCreate):
    """Report a new incident."""
    valid_severities = [s.value for s in IncidentSeverity]
    if body.severity not in valid_severities:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity '{body.severity}'. Must be one of: {', '.join(valid_severities)}",
        )

    incident = repository.repo.create_incident(
        type=body.type,
        severity=body.severity,
        description=body.description,
        reported_by=body.reported_by,
        location=body.location,
    )
    return schemas.IncidentResponse(**incident.to_dict())


@app.get("/incidents/{incident_id}", response_model=schemas.IncidentResponse)
async def get_incident(incident_id: str):
    """Get an incident by ID."""
    incident = repository.repo.get_incident(incident_id)
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return schemas.IncidentResponse(**incident.to_dict())


@app.patch("/incidents/{incident_id}", response_model=schemas.IncidentResponse)
async def update_incident(incident_id: str, body: schemas.IncidentUpdate):
    """Update an incident."""
    update_fields = body.model_dump(exclude_unset=True)
    incident = repository.repo.update_incident(incident_id, **update_fields)
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return schemas.IncidentResponse(**incident.to_dict())


@app.post("/incidents/{incident_id}/investigate", response_model=schemas.IncidentResponse)
async def investigate_incident(incident_id: str):
    """Begin investigation on an incident."""
    incident = repository.repo.investigate(incident_id)
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return schemas.IncidentResponse(**incident.to_dict())


@app.post("/incidents/{incident_id}/resolve", response_model=schemas.IncidentResponse)
async def resolve_incident(incident_id: str, body: schemas.ResolveRequest):
    """Resolve an incident."""
    incident = repository.repo.resolve(incident_id, resolution=body.resolution)
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return schemas.IncidentResponse(**incident.to_dict())


@app.post("/incidents/{incident_id}/notes", response_model=schemas.NoteResponse, status_code=201)
async def add_note(incident_id: str, body: schemas.NoteCreate):
    """Add an investigation note."""
    note = repository.repo.add_note(
        incident_id=incident_id,
        author=body.author,
        content=body.content,
    )
    if not note:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return schemas.NoteResponse(**note)
