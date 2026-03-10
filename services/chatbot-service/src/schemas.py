"""
Pydantic response schemas for the Chatbot service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ChatIntentResponse(BaseModel):
    id: str
    name: str
    patterns: List[str]
    responses: List[str]
    priority: int


class ChatIntentListResponse(BaseModel):
    intents: List[ChatIntentResponse]
    total: int


class ChatIntentCreateRequest(BaseModel):
    name: str
    patterns: List[str]
    responses: List[str]
    priority: int = 1


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    messages: List[Dict]
    status: str
    started_at: str


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


class SendMessageRequest(BaseModel):
    user_id: str
    message: str


class SendMessageResponse(BaseModel):
    conversation_id: str
    user_message: Dict
    bot_response: Dict
    matched_intent: Optional[str] = None


class ChatStatsResponse(BaseModel):
    total_conversations: int
    by_status: Dict[str, int]
    total_messages: int
    top_intents: List[Dict]
