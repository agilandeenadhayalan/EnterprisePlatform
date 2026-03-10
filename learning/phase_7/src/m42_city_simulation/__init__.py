"""
M42: City Simulation (Capstone) — agent-based modeling, dispatch, pricing, analytics.

This capstone module brings together concepts from the entire platform into
a city-scale simulation: autonomous driver and rider agents, discrete-event
simulation engine, dispatch and pricing policies, and analytics pipelines
that measure system-level KPIs like utilization, wait times, and throughput.
"""

from .agent_model import (
    Position,
    AgentState,
    Agent,
    DriverAgent,
    RiderAgent,
    RideRequest,
)
from .simulation_engine import (
    SimulationClock,
    Event,
    EventQueue,
    SimulationEngine,
    SimulationConfig,
)
from .city_integration import (
    DispatchPolicy,
    NearestDriverDispatch,
    ScoredDispatch,
    DynamicPricing,
    ETAEstimator,
    CityOrchestrator,
)
from .analytics_pipeline import (
    TickMetrics,
    MetricsCollector,
    KPICalculator,
    SimulationReport,
    ScenarioComparator,
)
