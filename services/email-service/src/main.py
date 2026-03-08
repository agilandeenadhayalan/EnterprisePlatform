"""
Email Service — FastAPI application.

ROUTES:
  POST /email/send          — Send a single email
  POST /email/send-template — Send an email using a template
  GET  /email/templates     — List available email templates
  GET  /health              — Health check (provided by create_app)
"""

import sys
from pathlib import Path

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


app = create_app(
    title="Email Service",
    version="0.1.0",
    description="Email delivery for Smart Mobility Platform",
)

email_repo = repository.EmailRepository()


# ── Routes ──


@app.post("/email/send", response_model=schemas.EmailSendResponse, status_code=201)
async def send_email(body: schemas.EmailSendRequest):
    """Send a single email."""
    message_id = await email_repo.send_email(
        to=body.to,
        subject=body.subject,
        body=body.body,
        is_html=body.is_html,
    )
    return schemas.EmailSendResponse(
        message_id=message_id,
        status="queued",
        to=body.to,
    )


@app.post("/email/send-template", response_model=schemas.EmailSendResponse, status_code=201)
async def send_template_email(body: schemas.EmailSendTemplateRequest):
    """Send an email using a pre-defined template."""
    message_id = await email_repo.send_template_email(
        to=body.to,
        template_id=body.template_id,
        variables=body.variables,
    )
    return schemas.EmailSendResponse(
        message_id=message_id,
        status="queued",
        to=body.to,
    )


@app.get("/email/templates", response_model=schemas.EmailTemplateListResponse)
async def list_templates():
    """List all available email templates."""
    templates = await email_repo.get_templates()
    return schemas.EmailTemplateListResponse(
        templates=[
            schemas.EmailTemplateResponse(**t)
            for t in templates
        ],
        count=len(templates),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
