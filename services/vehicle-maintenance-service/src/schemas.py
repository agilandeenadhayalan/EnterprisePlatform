"""Pydantic schemas for vehicle maintenance service."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class CreateMaintenanceRequest(BaseModel):
    vehicle_id: str
    maintenance_type: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    service_provider: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    next_due_at: Optional[datetime] = None


class MaintenanceResponse(BaseModel):
    id: str
    vehicle_id: str
    maintenance_type: str
    status: str
    description: Optional[str] = None
    cost: Optional[float] = None
    currency: str = "USD"
    service_provider: Optional[str] = None
    parts_replaced: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    next_due_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MaintenanceListResponse(BaseModel):
    records: List[MaintenanceResponse]
    count: int
