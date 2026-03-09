"""
Test Data Generator Service — FastAPI application.

Generates synthetic ride, location, and payment events for testing the
Smart Mobility Platform pipeline. Supports continuous and batch generation modes.

ROUTES:
  POST /generate/start      — Start generating events (mode, events_per_second, duration)
  POST /generate/stop       — Stop event generation
  GET  /generate/status     — Generation status (is_running, events_generated, elapsed_time)
  POST /generate/batch      — Generate a specific batch of events (count, event_type)
  GET  /generate/templates  — List available event templates (ride, location, payment, driver)
  GET  /health              — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException

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
    description="Synthetic event generator for testing the Smart Mobility Platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/generate/start", response_model=schemas.StartStopResponse, status_code=200)
async def start_generation(body: schemas.StartGenerationRequest):
    """Start generating events with the specified mode and rate."""
    # Validate mode
    if body.mode not in repository.VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: '{body.mode}'. Supported: {sorted(repository.VALID_MODES)}",
        )

    # Validate events_per_second
    if body.events_per_second < 1:
        raise HTTPException(status_code=400, detail="events_per_second must be at least 1")

    # Validate duration
    if body.duration_seconds < 1:
        raise HTTPException(status_code=400, detail="duration_seconds must be at least 1")

    status = repository.repo.start(
        mode=body.mode,
        events_per_second=body.events_per_second,
        duration_seconds=body.duration_seconds,
    )
    return schemas.StartStopResponse(
        message=f"Generation completed in {body.mode} mode",
        status=schemas.GeneratorStatusResponse(**status.to_dict()),
    )


@app.post("/generate/stop", response_model=schemas.StartStopResponse, status_code=200)
async def stop_generation():
    """Stop event generation."""
    status = repository.repo.stop()
    return schemas.StartStopResponse(
        message="Generation stopped",
        status=schemas.GeneratorStatusResponse(**status.to_dict()),
    )


@app.get("/generate/status", response_model=schemas.GeneratorStatusResponse)
async def generation_status():
    """Get current generation status."""
    status = repository.repo.get_status()
    return schemas.GeneratorStatusResponse(**status.to_dict())


@app.post("/generate/batch", response_model=schemas.BatchGenerateResponse, status_code=201)
async def batch_generate(body: schemas.BatchGenerateRequest):
    """Generate a specific batch of events."""
    # Validate event type
    if body.event_type not in repository.VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type: '{body.event_type}'. "
                   f"Supported: {sorted(repository.VALID_EVENT_TYPES)}",
        )

    # Validate count
    if body.count < 1:
        raise HTTPException(status_code=400, detail="count must be at least 1")

    if body.count > 10000:
        raise HTTPException(status_code=400, detail="count must not exceed 10000")

    events = repository.repo.generate_batch(count=body.count, event_type=body.event_type)
    return schemas.BatchGenerateResponse(
        events=[schemas.GeneratedEventResponse(**e.to_dict()) for e in events],
        total=len(events),
        event_type=body.event_type,
    )


@app.get("/generate/templates", response_model=schemas.EventTemplateListResponse)
async def list_templates():
    """List available event templates (ride, location, payment, driver)."""
    templates = repository.repo.get_templates()
    return schemas.EventTemplateListResponse(
        templates=[schemas.EventTemplateResponse(**t.to_dict()) for t in templates],
        total=len(templates),
    )
