"""
Presence Service — FastAPI application.

ROUTES:
  POST /users/{id}/heartbeat    — Record a heartbeat (user is online)
  GET  /users/{id}/presence     — Get user's presence status
  GET  /presence/online-count   — Get count of online users
  GET  /health                  — Health check (provided by create_app)
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
    title="Presence Service",
    version="0.1.0",
    description="Online presence tracking for Smart Mobility Platform",
)

presence_repo = repository.PresenceRepository(
    ttl_seconds=service_config.settings.heartbeat_ttl_seconds
)


# ── Routes ──


@app.post("/users/{user_id}/heartbeat", response_model=schemas.HeartbeatResponse)
async def heartbeat(user_id: str, body: schemas.HeartbeatRequest):
    """Record a heartbeat to indicate user is online."""
    await presence_repo.record_heartbeat(user_id, body.status)
    return schemas.HeartbeatResponse(
        user_id=user_id,
        status=body.status,
        ttl_seconds=service_config.settings.heartbeat_ttl_seconds,
    )


@app.get("/users/{user_id}/presence", response_model=schemas.PresenceResponse)
async def get_presence(user_id: str):
    """Get current presence status for a user."""
    data = await presence_repo.get_presence(user_id)
    if not data:
        return schemas.PresenceResponse(user_id=user_id, is_online=False)
    return schemas.PresenceResponse(
        user_id=user_id,
        is_online=data["is_online"],
        status=data.get("status"),
        last_seen=data.get("last_seen"),
    )


@app.get("/presence/online-count", response_model=schemas.OnlineCountResponse)
async def get_online_count():
    """Get the count of currently online users."""
    count = await presence_repo.get_online_count()
    return schemas.OnlineCountResponse(online_count=count)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
