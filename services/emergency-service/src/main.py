"""
Emergency Service — FastAPI application.

SOS alerts and emergency response coordination.

ROUTES:
  POST   /emergency/sos                       — Trigger SOS alert
  GET    /emergency/alerts                     — List active emergency alerts
  GET    /emergency/alerts/{id}                — Get alert details
  PATCH  /emergency/alerts/{id}                — Update alert (acknowledge)
  POST   /emergency/alerts/{id}/dispatch       — Dispatch emergency responder
  POST   /emergency/alerts/{id}/resolve        — Resolve emergency
  GET    /emergency/responders                 — List available responders
  GET    /health                               — Health check (provided by create_app)
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
from models import EmergencyType


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="SOS alerts and emergency response coordination",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/emergency/sos", response_model=schemas.EmergencyAlertResponse, status_code=201)
async def trigger_sos(body: schemas.SOSRequest):
    """Trigger an SOS alert."""
    valid_types = [t.value for t in EmergencyType]
    if body.emergency_type not in valid_types:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid emergency type '{body.emergency_type}'. Must be one of: {', '.join(valid_types)}",
        )

    alert = repository.repo.create_sos(
        emergency_type=body.emergency_type,
        reporter_id=body.reporter_id,
        location=body.location,
        description=body.description,
    )
    return schemas.EmergencyAlertResponse(**alert.to_dict())


@app.get("/emergency/alerts", response_model=list[schemas.EmergencyAlertResponse])
async def list_alerts():
    """List active emergency alerts."""
    alerts = repository.repo.list_alerts()
    return [schemas.EmergencyAlertResponse(**a.to_dict()) for a in alerts]


@app.get("/emergency/alerts/{alert_id}", response_model=schemas.EmergencyAlertResponse)
async def get_alert(alert_id: str):
    """Get an emergency alert by ID."""
    alert = repository.repo.get_alert(alert_id)
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return schemas.EmergencyAlertResponse(**alert.to_dict())


@app.patch("/emergency/alerts/{alert_id}", response_model=schemas.EmergencyAlertResponse)
async def update_alert(alert_id: str, body: schemas.AlertUpdate):
    """Update an emergency alert (e.g. acknowledge)."""
    update_fields = body.model_dump(exclude_unset=True)
    alert = repository.repo.update_alert(alert_id, **update_fields)
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return schemas.EmergencyAlertResponse(**alert.to_dict())


@app.post("/emergency/alerts/{alert_id}/dispatch", response_model=schemas.EmergencyAlertResponse)
async def dispatch_responder(alert_id: str, body: schemas.DispatchRequest):
    """Dispatch an emergency responder."""
    alert = repository.repo.dispatch_responder(alert_id, body.responder_id)
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' or responder '{body.responder_id}' not found")
    return schemas.EmergencyAlertResponse(**alert.to_dict())


@app.post("/emergency/alerts/{alert_id}/resolve", response_model=schemas.EmergencyAlertResponse)
async def resolve_alert(alert_id: str):
    """Resolve an emergency alert."""
    alert = repository.repo.resolve_alert(alert_id)
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return schemas.EmergencyAlertResponse(**alert.to_dict())


@app.get("/emergency/responders", response_model=list[schemas.ResponderResponse])
async def list_responders():
    """List available emergency responders."""
    responders = repository.repo.list_responders()
    return [schemas.ResponderResponse(**r.to_dict()) for r in responders]
