"""
Pydantic request/response schemas for the audit service API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class AuditLogCreate(BaseModel):
    """POST /audit/logs — record an audit event."""
    action: str = Field(..., description="Action: create, read, update, delete, login, export, approve")
    entity_type: str = Field(..., description="Type of entity acted upon")
    entity_id: str = Field(..., description="ID of the entity")
    actor: str = Field(..., description="Who performed the action")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional details")
    region: Optional[str] = Field(default=None, description="Region where action occurred")
    ip_address: Optional[str] = Field(default=None, description="IP address of actor")


class AuditSearchRequest(BaseModel):
    """POST /audit/logs/search — advanced search."""
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    actor: Optional[str] = None
    action: Optional[str] = None
    region: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ── Response schemas ──

class AuditLogResponse(BaseModel):
    """An audit log entry."""
    id: str
    action: str
    entity_type: str
    entity_id: str
    actor: str
    details: dict[str, Any] = {}
    region: Optional[str] = None
    ip_address: Optional[str] = None
    entry_hash: str
    previous_hash: str
    created_at: datetime


class AuditStatsResponse(BaseModel):
    """Audit statistics."""
    total_entries: int
    by_action: dict[str, int]
    by_entity_type: dict[str, int]
    by_actor: dict[str, int]
    chain_valid: bool
