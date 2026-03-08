"""Pydantic schemas for the fare split service API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ParticipantInput(BaseModel):
    user_id: str
    share_amount: float = Field(..., gt=0)

class CreateSplitRequest(BaseModel):
    trip_id: str
    initiator_id: str
    total_amount: float = Field(..., gt=0)
    participants: list[ParticipantInput] = Field(..., min_length=2)

class ParticipantResponse(BaseModel):
    id: str
    split_id: str
    user_id: str
    share_amount: float
    status: str
    created_at: datetime

class SplitResponse(BaseModel):
    id: str
    trip_id: str
    initiator_id: str
    total_amount: float
    status: str
    participants: list[ParticipantResponse] = []
    created_at: datetime

class AcceptSplitResponse(BaseModel):
    split_id: str
    user_id: str
    status: str
    message: str
