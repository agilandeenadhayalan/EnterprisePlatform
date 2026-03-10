"""
M40: Cost Optimization — right-sizing, unit economics, spot instances, cost allocation.

This module covers cloud cost optimization strategies for mobility platforms:
analyzing instance utilization to right-size resources, calculating unit
economics per trip, leveraging spot instances for savings, and implementing
cost allocation across teams and services.
"""

from .right_sizing import (
    InstanceMetrics,
    InstanceType,
    UtilizationAnalyzer,
    RightSizer,
    RightSizingReport,
)
from .unit_economics import (
    TripCostBreakdown,
    UnitEconomicsCalculator,
    CostTrend,
    PricingModel,
)
from .spot_instances import (
    SpotPricePoint,
    SpotMarket,
    SpotStrategy,
    SpotInstanceManager,
    FleetComposition,
)
from .cost_allocation import (
    CostTag,
    AllocationRule,
    CostAllocator,
    CostReport,
    ChargebackCalculator,
)
