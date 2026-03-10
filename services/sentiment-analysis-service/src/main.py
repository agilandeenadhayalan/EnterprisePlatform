"""
Sentiment Analysis Service — FastAPI application.

Sentiment analysis with aspect extraction for reviews and text.

ROUTES:
  POST /sentiment/analyze          — Analyze text
  GET  /sentiment/results          — List results
  GET  /sentiment/results/{id}     — Get result
  POST /sentiment/analyze-review   — Analyze review
  GET  /sentiment/reviews          — List review analyses
  GET  /sentiment/reviews/{id}     — Get review analysis
  GET  /sentiment/stats            — Sentiment statistics
  GET  /health                     — Health check (provided by create_app)
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
    description="Sentiment analysis with aspect extraction for reviews and text",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/sentiment/analyze", response_model=schemas.SentimentResultResponse, status_code=201)
async def analyze_text(req: schemas.AnalyzeTextRequest):
    """Analyze text for sentiment."""
    result = repository.repo.analyze_text(req.text)
    return schemas.SentimentResultResponse(**result.to_dict())


@app.get("/sentiment/results", response_model=schemas.SentimentResultListResponse)
async def list_results(
    sentiment: Optional[str] = Query(default=None, description="Filter by sentiment"),
):
    """List all sentiment results."""
    results = repository.repo.list_results(sentiment=sentiment)
    return schemas.SentimentResultListResponse(
        results=[schemas.SentimentResultResponse(**r.to_dict()) for r in results],
        total=len(results),
    )


@app.get("/sentiment/results/{result_id}", response_model=schemas.SentimentResultResponse)
async def get_result(result_id: str):
    """Get a sentiment result by ID."""
    result = repository.repo.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found")
    return schemas.SentimentResultResponse(**result.to_dict())


@app.post("/sentiment/analyze-review", response_model=schemas.ReviewAnalysisResponse, status_code=201)
async def analyze_review(req: schemas.AnalyzeReviewRequest):
    """Analyze a review with aspect sentiment extraction."""
    review = repository.repo.analyze_review(req.model_dump())
    return schemas.ReviewAnalysisResponse(**review.to_dict())


@app.get("/sentiment/reviews", response_model=schemas.ReviewAnalysisListResponse)
async def list_reviews():
    """List all review analyses."""
    reviews = repository.repo.list_reviews()
    return schemas.ReviewAnalysisListResponse(
        reviews=[schemas.ReviewAnalysisResponse(**r.to_dict()) for r in reviews],
        total=len(reviews),
    )


@app.get("/sentiment/reviews/{review_id}", response_model=schemas.ReviewAnalysisResponse)
async def get_review(review_id: str):
    """Get a review analysis by ID."""
    review = repository.repo.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found")
    return schemas.ReviewAnalysisResponse(**review.to_dict())


@app.get("/sentiment/stats", response_model=schemas.SentimentStatsResponse)
async def sentiment_stats():
    """Get sentiment analysis statistics."""
    stats = repository.repo.get_stats()
    return schemas.SentimentStatsResponse(**stats)
