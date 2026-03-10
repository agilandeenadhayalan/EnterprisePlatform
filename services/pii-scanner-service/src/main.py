"""
PII Scanner Service — FastAPI application.

PII detection using regex patterns with masking capabilities.

ROUTES:
  POST   /pii/scan                 — Scan text for PII
  POST   /pii/scan-dataset         — Scan a named dataset
  GET    /pii/scan-results         — List past scan results
  GET    /pii/scan-results/{id}    — Get specific result
  GET    /pii/patterns             — List available detection patterns
  POST   /pii/mask                 — Mask PII in provided text
  GET    /health                   — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

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
    description="PII detection and masking using regex patterns",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/pii/scan", response_model=schemas.ScanResponse)
async def scan_text(body: schemas.ScanTextRequest):
    """Scan text for PII."""
    result = repository.repo.scan_text(text=body.text, source=body.source)
    return schemas.ScanResponse(**result.to_dict())


@app.post("/pii/scan-dataset", response_model=schemas.ScanResponse)
async def scan_dataset(body: schemas.ScanDatasetRequest):
    """Scan a named dataset for PII."""
    result = repository.repo.scan_dataset(
        dataset_name=body.dataset_name,
        sample_data=body.sample_data,
    )
    return schemas.ScanResponse(**result.to_dict())


@app.get("/pii/scan-results", response_model=list[schemas.ScanResponse])
async def list_scan_results():
    """List past scan results."""
    results = repository.repo.list_scan_results()
    return [schemas.ScanResponse(**r.to_dict()) for r in results]


@app.get("/pii/scan-results/{scan_id}", response_model=schemas.ScanResponse)
async def get_scan_result(scan_id: str):
    """Get a specific scan result."""
    result = repository.repo.get_scan_result(scan_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Scan result '{scan_id}' not found")
    return schemas.ScanResponse(**result.to_dict())


@app.get("/pii/patterns", response_model=list[schemas.PatternResponse])
async def list_patterns():
    """List available PII detection patterns."""
    patterns = repository.repo.get_patterns()
    return [schemas.PatternResponse(**p) for p in patterns]


@app.post("/pii/mask", response_model=schemas.MaskResponse)
async def mask_text(body: schemas.MaskRequest):
    """Mask PII in provided text."""
    valid_strategies = ["redact", "partial", "hash"]
    if body.strategy not in valid_strategies:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy '{body.strategy}'. Must be one of: {', '.join(valid_strategies)}",
        )
    result = repository.repo.mask_text(text=body.text, strategy=body.strategy)
    return schemas.MaskResponse(**result)
