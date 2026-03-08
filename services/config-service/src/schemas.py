"""
Pydantic request/response schemas for the config service API.

These define the API contract — what clients send and receive.
Config values use JSONB, so 'value' can be any JSON-serializable type:
strings, numbers, booleans, dicts, or lists.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    """Single configuration entry — returned in detail and list endpoints."""
    service: str
    key: str
    value: Any
    description: Optional[str] = None
    version: int
    updated_at: datetime


class SetConfigRequest(BaseModel):
    """PUT /configs/{service}/{key} — set or update a configuration value."""
    value: Any = Field(..., description="Configuration value (any JSON type)")
    description: Optional[str] = Field(None, description="Human-readable description of this config entry")


class ConfigListResponse(BaseModel):
    """GET /configs — list of configuration entries."""
    configs: list[ConfigResponse]
    count: int
