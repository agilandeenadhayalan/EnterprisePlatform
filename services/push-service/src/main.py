"""
Push Service — FastAPI application.

ROUTES:
  POST /push/send         — Send a push notification to a single device
  POST /push/send-bulk    — Send push notifications to multiple devices
  GET  /push/status/{id}  — Get delivery status of a push notification
  GET  /health            — Health check (provided by create_app)
"""

import sys
from pathlib import Path

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.errors import not_found

import config as service_config
import schemas
import repository


app = create_app(
    title="Push Service",
    version="0.1.0",
    description="Push notification delivery for Smart Mobility Platform",
)

push_repo = repository.PushRepository()


# ── Routes ──


@app.post("/push/send", response_model=schemas.PushSendResponse, status_code=201)
async def send_push(body: schemas.PushSendRequest):
    """Send a push notification to a single device."""
    message_id = await push_repo.send_push(
        device_token=body.device_token,
        title=body.title,
        body=body.body,
        data=body.data,
    )
    return schemas.PushSendResponse(
        message_id=message_id,
        status="sent",
        provider=service_config.settings.push_provider,
    )


@app.post("/push/send-bulk", response_model=schemas.PushBulkResponse, status_code=201)
async def send_push_bulk(body: schemas.PushSendBulkRequest):
    """Send push notifications to multiple devices."""
    message_ids, sent, failed = await push_repo.send_push_bulk(
        device_tokens=body.device_tokens,
        title=body.title,
        body=body.body,
        data=body.data,
    )
    return schemas.PushBulkResponse(
        total=len(body.device_tokens),
        sent=sent,
        failed=failed,
        message_ids=message_ids,
    )


@app.get("/push/status/{message_id}", response_model=schemas.PushStatusResponse)
async def get_push_status(message_id: str):
    """Get delivery status of a push notification."""
    status = await push_repo.get_status(message_id)
    if not status:
        raise not_found("Push message", message_id)
    return schemas.PushStatusResponse(message_id=message_id, status=status)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
