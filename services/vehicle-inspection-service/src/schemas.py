"""Pydantic schemas for vehicle inspection service."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class CreateInspectionRequest(BaseModel):
    vehicle_id: str
    inspector_id: Optional[str] = None
    inspection_type: str = Field(..., min_length=1, max_length=50)
    notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class UpdateInspectionStatusRequest(BaseModel):
    status: str = Field(..., description="New inspection status")
    notes: Optional[str] = None
    findings: Optional[Dict[str, Any]] = None


class InspectionResponse(BaseModel):
    id: str
    vehicle_id: str
    inspector_id: Optional[str] = None
    inspection_type: str
    status: str
    notes: Optional[str] = None
    findings: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class InspectionListResponse(BaseModel):
    inspections: List[InspectionResponse]
    count: int
