"""
Chatbot Service — FastAPI application.

Intent-based chatbot with conversation management and pattern matching.

ROUTES:
  POST /chatbot/message                  — Send message
  GET  /chatbot/conversations            — List conversations
  GET  /chatbot/conversations/{id}       — Get conversation with messages
  POST /chatbot/conversations/{id}/close — Close conversation
  GET  /chatbot/intents                  — List intents
  POST /chatbot/intents                  — Create intent
  GET  /chatbot/intents/{id}             — Get intent
  GET  /chatbot/stats                    — Chat statistics
  GET  /health                           — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query, HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Intent-based chatbot with conversation management and pattern matching",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/chatbot/message", response_model=schemas.SendMessageResponse)
async def send_message(req: schemas.SendMessageRequest):
    """Send a message to the chatbot."""
    result = repository.repo.send_message(req.user_id, req.message)
    return schemas.SendMessageResponse(**result)


@app.get("/chatbot/conversations", response_model=schemas.ConversationListResponse)
async def list_conversations(
    user_id: Optional[str] = Query(default=None, description="Filter by user_id"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List all conversations."""
    convs = repository.repo.list_conversations(user_id=user_id, status=status)
    return schemas.ConversationListResponse(
        conversations=[schemas.ConversationResponse(**c.to_dict()) for c in convs],
        total=len(convs),
    )


@app.get("/chatbot/conversations/{conv_id}", response_model=schemas.ConversationResponse)
async def get_conversation(conv_id: str):
    """Get a conversation with messages."""
    conv = repository.repo.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found")
    return schemas.ConversationResponse(**conv.to_dict())


@app.post("/chatbot/conversations/{conv_id}/close", response_model=schemas.ConversationResponse)
async def close_conversation(conv_id: str):
    """Close a conversation."""
    conv = repository.repo.close_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found")
    return schemas.ConversationResponse(**conv.to_dict())


@app.get("/chatbot/intents", response_model=schemas.ChatIntentListResponse)
async def list_intents():
    """List all chat intents."""
    intents = repository.repo.list_intents()
    return schemas.ChatIntentListResponse(
        intents=[schemas.ChatIntentResponse(**i.to_dict()) for i in intents],
        total=len(intents),
    )


@app.post("/chatbot/intents", response_model=schemas.ChatIntentResponse, status_code=201)
async def create_intent(req: schemas.ChatIntentCreateRequest):
    """Create a new chat intent."""
    intent = repository.repo.create_intent(req.model_dump())
    return schemas.ChatIntentResponse(**intent.to_dict())


@app.get("/chatbot/intents/{intent_id}", response_model=schemas.ChatIntentResponse)
async def get_intent(intent_id: str):
    """Get a chat intent by ID."""
    intent = repository.repo.get_intent(intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail=f"Intent '{intent_id}' not found")
    return schemas.ChatIntentResponse(**intent.to_dict())


@app.get("/chatbot/stats", response_model=schemas.ChatStatsResponse)
async def chat_stats():
    """Get chat statistics."""
    stats = repository.repo.get_stats()
    return schemas.ChatStatsResponse(**stats)
