"""
Pydantic request/response schemas for the test data generator API.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class StartGenerationRequest(BaseModel):
    """POST /generate/start — start event generation."""
    mode: str = Field(default="synthetic", description="Generation mode: replay, synthetic, stress")
    events_per_second: int = Field(default=10, description="Events to generate per second")
    duration_seconds: int = Field(default=60, description="Duration in seconds")


class BatchGenerateRequest(BaseModel):
    """POST /generate/batch — generate a batch of events."""
    count: int = Field(default=100, description="Number of events to generate")
    event_type: str = Field(default="ride", description="Event type: ride, location, payment, driver")


# ── Response schemas ──


class GeneratorStatusResponse(BaseModel):
    """Generator status."""
    is_running: bool
    mode: Optional[str] = None
    events_generated: int
    events_per_second: int
    elapsed_seconds: float
    started_at: Optional[str] = None


class EventTemplateResponse(BaseModel):
    """Event template definition."""
    template_id: str
    name: str
    description: str
    event_type: str
    fields: list[dict[str, str]]
    sample: dict[str, Any]


class EventTemplateListResponse(BaseModel):
    """List of event templates."""
    templates: list[EventTemplateResponse]
    total: int


class GeneratedEventResponse(BaseModel):
    """A single generated event."""
    event_id: str
    event_type: str
    timestamp: str
    data: dict[str, Any]


class BatchGenerateResponse(BaseModel):
    """Result of batch event generation."""
    events: list[GeneratedEventResponse]
    total: int
    event_type: str


class StartStopResponse(BaseModel):
    """Response for start/stop operations."""
    message: str
    status: GeneratorStatusResponse
