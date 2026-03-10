"""
M32: Demand Forecasting — Spatio-temporal modeling, weather integration,
uncertainty quantification, and demand pattern detection.

This module covers how ride-hailing platforms predict where and when riders
will request trips. Accurate demand forecasting drives driver positioning,
surge pricing, and fleet management.
"""

from .spatio_temporal import GridCell, TimeSlot, SpatioTemporalGrid
from .weather_integration import WeatherCondition, WeatherFeatures, WeatherImpactModel
from .uncertainty import PredictionInterval, QuantileRegression, MonteCarloDropout
from .demand_patterns import PatternType, DemandPattern, DemandDecomposition
