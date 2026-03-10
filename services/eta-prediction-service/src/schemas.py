"""
Pydantic response schemas for the ETA Prediction service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ETAPredictionResponse(BaseModel):
    id: str
    route_id: str
    origin: Dict
    destination: Dict
    predicted_minutes: float
    actual_minutes: Optional[float] = None
    confidence: float
    method: str
    features: Dict
    created_at: str


class ETAPredictionListResponse(BaseModel):
    predictions: List[ETAPredictionResponse]
    total: int


class ETAPredictRequest(BaseModel):
    route_id: str
    origin: Dict
    destination: Dict
    method: str = "historical"


class RoadSegmentResponse(BaseModel):
    id: str
    name: str
    start_point: Dict
    end_point: Dict
    speed_kmh: float
    congestion_level: str
    distance_km: float


class RoadSegmentDetailResponse(BaseModel):
    id: str
    name: str
    start_point: Dict
    end_point: Dict
    speed_kmh: float
    congestion_level: str
    distance_km: float
    speed_profiles: List[Dict]


class RoadSegmentListResponse(BaseModel):
    segments: List[RoadSegmentResponse]
    total: int


class SpeedObservationRequest(BaseModel):
    hour: int
    speed: float


class SpeedProfileResponse(BaseModel):
    segment_id: str
    hour: int
    avg_speed: float
    stddev: float


class ETAStatsResponse(BaseModel):
    total_predictions: int
    by_method: Dict[str, int]
    avg_confidence: float
