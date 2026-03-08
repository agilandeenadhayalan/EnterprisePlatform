"""
SMS Service — FastAPI application.

ROUTES:
  POST /sms/send         — Send an SMS message
  POST /sms/send-otp     — Send an OTP code via SMS
  GET  /sms/status/{id}  — Get delivery status of an SMS
  GET  /health           — Health check (provided by create_app)
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
    title="SMS Service",
    version="0.1.0",
    description="SMS delivery for Smart Mobility Platform",
)

sms_repo = repository.SmsRepository()


# ── Routes ──


@app.post("/sms/send", response_model=schemas.SmsSendResponse, status_code=201)
async def send_sms(body: schemas.SmsSendRequest):
    """Send an SMS message to a phone number."""
    message_id = await sms_repo.send_sms(to=body.to, message=body.message)
    return schemas.SmsSendResponse(
        message_id=message_id,
        status="queued",
        to=body.to,
        provider=service_config.settings.sms_provider,
    )


@app.post("/sms/send-otp", response_model=schemas.SmsSendResponse, status_code=201)
async def send_otp(body: schemas.SmsSendOtpRequest):
    """Send an OTP code via SMS."""
    message_id = await sms_repo.send_otp_sms(to=body.to, otp_code=body.otp_code)
    return schemas.SmsSendResponse(
        message_id=message_id,
        status="queued",
        to=body.to,
        provider=service_config.settings.sms_provider,
    )


@app.get("/sms/status/{message_id}", response_model=schemas.SmsStatusResponse)
async def get_sms_status(message_id: str):
    """Get delivery status of an SMS."""
    status_data = await sms_repo.get_status(message_id)
    if not status_data:
        raise not_found("SMS message", message_id)
    return schemas.SmsStatusResponse(
        message_id=message_id,
        status=status_data["status"],
        to=status_data.get("to"),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
