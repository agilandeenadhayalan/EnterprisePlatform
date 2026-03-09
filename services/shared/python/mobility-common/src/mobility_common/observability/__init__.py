"""
Observability library — metrics, tracing, logging, and health checks.

Provides shared observability primitives used across all platform services
for monitoring, debugging, and operational visibility.
"""

from .metrics import Counter, Gauge, Histogram, MetricsClient
from .tracing import Span, TraceContext, TracingClient
from .logging import StructuredLogger, LogEntry
from .health import HealthProbe, HealthResult, HealthChecker

__all__ = [
    "Counter", "Gauge", "Histogram", "MetricsClient",
    "Span", "TraceContext", "TracingClient",
    "StructuredLogger", "LogEntry",
    "HealthProbe", "HealthResult", "HealthChecker",
]
