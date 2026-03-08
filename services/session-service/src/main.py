"""
Session Service — FastAPI application.

ROUTES:
  GET    /sessions              — List active sessions for current user
  GET    /sessions/{session_id} — Get session details
  DELETE /sessions/{session_id} — Revoke a specific session
  GET    /sessions/active/count — Count of active sessions
  GET    /health                — Health check (provided by create_app)

All routes require authentication (JWT Bearer token).
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, forbidden
from mobility_common.fastapi.middleware import get_current_user, TokenPayload

import config as session_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(session_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Session Service",
    version="0.1.0",
    description="Session management for Smart Mobility Platform — list, inspect, revoke sessions",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/sessions/active/count", response_model=schemas.SessionCountResponse)
async def get_active_session_count(
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the number of active (non-expired) sessions for the current user."""
    repo = repository.SessionRepository(db)
    count = await repo.count_active_sessions(user.sub)
    return schemas.SessionCountResponse(active_count=count)


@app.get("/sessions", response_model=schemas.SessionListResponse)
async def list_sessions(
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active sessions for the currently authenticated user."""
    repo = repository.SessionRepository(db)
    sessions = await repo.get_user_sessions(user.sub)

    session_list = [
        schemas.SessionResponse(
            id=str(s.id),
            user_id=str(s.user_id),
            device_info=s.device_info,
            ip_address=str(s.ip_address) if s.ip_address else None,
            created_at=s.created_at,
            expires_at=s.expires_at,
        )
        for s in sessions
    ]

    return schemas.SessionListResponse(sessions=session_list, count=len(session_list))


@app.get("/sessions/{session_id}", response_model=schemas.SessionResponse)
async def get_session(
    session_id: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific session. Users can only view their own sessions."""
    repo = repository.SessionRepository(db)
    session = await repo.get_session_by_id(session_id)

    if not session:
        raise not_found("Session", session_id)

    # Ensure users can only view their own sessions
    if str(session.user_id) != user.sub:
        raise forbidden("You can only view your own sessions")

    return schemas.SessionResponse(
        id=str(session.id),
        user_id=str(session.user_id),
        device_info=session.device_info,
        ip_address=str(session.ip_address) if session.ip_address else None,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


@app.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a specific session (logout from one device).

    Users can only revoke their own sessions.
    """
    repo = repository.SessionRepository(db)
    session = await repo.get_session_by_id(session_id)

    if not session:
        raise not_found("Session", session_id)

    # Ensure users can only revoke their own sessions
    if str(session.user_id) != user.sub:
        raise forbidden("You can only revoke your own sessions")

    await repo.delete_session(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=session_config.settings.service_port,
        reload=session_config.settings.debug,
    )
