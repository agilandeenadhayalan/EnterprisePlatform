"""
Pydantic response schemas for the Sentiment Analysis service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class SentimentResultResponse(BaseModel):
    id: str
    text: str
    sentiment: str
    score: float
    aspects: List[Dict]
    created_at: str


class SentimentResultListResponse(BaseModel):
    results: List[SentimentResultResponse]
    total: int


class AnalyzeTextRequest(BaseModel):
    text: str


class AnalyzeReviewRequest(BaseModel):
    review_id: str
    text: str
    entity_type: str
    entity_id: str


class ReviewAnalysisResponse(BaseModel):
    id: str
    review_id: str
    entity_type: str
    entity_id: str
    overall_sentiment: str
    aspects: List[Dict]
    created_at: str


class ReviewAnalysisListResponse(BaseModel):
    reviews: List[ReviewAnalysisResponse]
    total: int


class SentimentStatsResponse(BaseModel):
    total_analyses: int
    by_sentiment: Dict[str, int]
    avg_score: float
