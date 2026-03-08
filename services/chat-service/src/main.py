"""
Chat Service — FastAPI application.

ROUTES:
  POST /rooms                 — Create a new chat room
  GET  /rooms/{id}/messages   — Get messages for a chat room
  POST /rooms/{id}/messages   — Send a message to a chat room
  GET  /trips/{id}/chat       — Get chat room for a trip
  GET  /health                — Health check (provided by create_app)
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
    title="Chat Service",
    version="0.1.0",
    description="Chat rooms and messaging for Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/rooms", response_model=schemas.ChatRoomResponse, status_code=201)
async def create_room(
    body: schemas.CreateRoomRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat room."""
    repo = repository.ChatRepository(db)
    room = await repo.create_room(
        participant_ids=body.participant_ids,
        room_type=body.room_type,
        trip_id=body.trip_id,
    )
    return schemas.ChatRoomResponse(
        id=str(room.id),
        trip_id=str(room.trip_id) if room.trip_id else None,
        room_type=room.room_type,
        participant_ids=room.participant_ids.split(","),
        created_at=room.created_at,
    )


@app.get("/rooms/{room_id}/messages", response_model=schemas.ChatMessageListResponse)
async def get_room_messages(
    room_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a chat room."""
    repo = repository.ChatRepository(db)
    messages = await repo.get_room_messages(room_id)
    return schemas.ChatMessageListResponse(
        messages=[
            schemas.ChatMessageResponse(
                id=str(m.id),
                room_id=str(m.room_id),
                sender_id=str(m.sender_id),
                message=m.message,
                message_type=m.message_type,
                created_at=m.created_at,
            )
            for m in messages
        ],
        count=len(messages),
    )


@app.post("/rooms/{room_id}/messages", response_model=schemas.ChatMessageResponse, status_code=201)
async def send_message(
    room_id: str,
    body: schemas.SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to a chat room."""
    repo = repository.ChatRepository(db)
    room = await repo.get_room(room_id)
    if not room:
        raise not_found("Chat room", room_id)
    msg = await repo.send_message(
        room_id=room_id,
        sender_id=body.sender_id,
        message=body.message,
        message_type=body.message_type,
    )
    return schemas.ChatMessageResponse(
        id=str(msg.id),
        room_id=str(msg.room_id),
        sender_id=str(msg.sender_id),
        message=msg.message,
        message_type=msg.message_type,
        created_at=msg.created_at,
    )


@app.get("/trips/{trip_id}/chat", response_model=schemas.ChatRoomResponse)
async def get_trip_chat(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the chat room associated with a trip."""
    repo = repository.ChatRepository(db)
    room = await repo.get_room_by_trip(trip_id)
    if not room:
        raise not_found("Chat room for trip", trip_id)
    return schemas.ChatRoomResponse(
        id=str(room.id),
        trip_id=str(room.trip_id) if room.trip_id else None,
        room_type=room.room_type,
        participant_ids=room.participant_ids.split(","),
        created_at=room.created_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
