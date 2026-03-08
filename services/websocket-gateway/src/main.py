"""
WebSocket Gateway — FastAPI application.

ROUTES:
  GET  /health     — Health check (provided by create_app)
  GET  /ws/info    — WebSocket gateway stats
  POST /broadcast  — Broadcast a message to connected clients

Note: Actual WebSocket handling (ws:// upgrade) is complex and would
be implemented with FastAPI's WebSocket support. This service provides
HTTP health/admin endpoints and a stub broadcast endpoint.
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
    title="WebSocket Gateway",
    version="0.1.0",
    description="Real-time WebSocket relay for Smart Mobility Platform",
)

ws_manager = repository.WsConnectionManager()


# ── Routes ──


@app.get("/ws/info", response_model=schemas.WsInfoResponse)
async def ws_info():
    """Get WebSocket gateway statistics."""
    info = await ws_manager.get_info()
    return schemas.WsInfoResponse(
        active_connections=info["active_connections"],
        max_connections=service_config.settings.ws_max_connections,
        uptime_seconds=info["uptime_seconds"],
        channels=info["channels"],
    )


@app.post("/broadcast", response_model=schemas.BroadcastResponse, status_code=201)
async def broadcast(body: schemas.BroadcastRequest):
    """Broadcast a message to connected WebSocket clients."""
    recipients = await ws_manager.broadcast(
        channel=body.channel,
        event=body.event,
        data=body.data,
        user_ids=body.user_ids,
    )
    return schemas.BroadcastResponse(
        channel=body.channel,
        event=body.event,
        recipients=recipients,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
