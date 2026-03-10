"""
Capacity Planning — project future load and recommend scaling strategies.

WHY THIS MATTERS:
Running out of capacity is how outages happen. If your traffic is growing
20% monthly and your current system handles 1000 RPS, you need to know
WHEN you'll hit the wall and HOW MUCH to scale. Capacity planning uses
growth projections, utilization analysis, and cost modeling to answer:

  - When will we run out of capacity? (time to exhaustion)
  - Are we over-provisioned (wasting money) or under-provisioned (risking outages)?
  - How should we scale (horizontal vs vertical) and what will it cost?

Key concepts:
  - Resource profiles: CPU/memory/network per request
  - Utilization analysis: avg vs peak vs p95 — different thresholds for different decisions
  - Growth projection: exponential growth is the default assumption for internet services
  - Scaling recommendations: horizontal (add instances) vs vertical (bigger instances)
"""

import math
from dataclasses import dataclass, field


@dataclass
class ResourceProfile:
    """Resource consumption per request.

    Attributes:
        cpu_per_request: CPU time in milliseconds per request
        memory_per_request_mb: memory consumed per request in MB
        network_per_request_kb: network bandwidth per request in KB
    """
    cpu_per_request: float
    memory_per_request_mb: float
    network_per_request_kb: float


@dataclass
class InstanceType:
    """Cloud instance specification and cost.

    Attributes:
        name: instance type name (e.g., "c5.2xlarge")
        vcpus: number of virtual CPUs
        memory_gb: total memory in GB
        cost_per_hour: on-demand hourly cost in USD
    """
    name: str
    vcpus: int
    memory_gb: float
    cost_per_hour: float


class UtilizationAnalyzer:
    """Analyze resource utilization to detect over/under-provisioning.

    Classifies the current state based on utilization thresholds:
      - Over-provisioned: average utilization below 30% (wasting money)
      - Under-provisioned: p95 utilization above 80% (risking outages)
      - Right-sized: between the two thresholds
    """

    def analyze(self, metrics: list[float]) -> dict:
        """Compute utilization statistics from a list of utilization samples.

        Args:
            metrics: list of utilization values (0.0 to 1.0)

        Returns:
            dict with avg, peak, p95 utilization values
        """
        if not metrics:
            return {"avg": 0.0, "peak": 0.0, "p95": 0.0}

        sorted_metrics = sorted(metrics)
        avg = sum(metrics) / len(metrics)
        peak = max(metrics)

        # p95
        idx = int(0.95 * (len(sorted_metrics) - 1))
        p95 = sorted_metrics[idx]

        return {
            "avg": round(avg, 4),
            "peak": round(peak, 4),
            "p95": round(p95, 4),
        }

    def is_over_provisioned(self, avg_util: float, threshold: float = 0.3) -> bool:
        """True if average utilization is below the threshold (wasting money)."""
        return avg_util < threshold

    def is_under_provisioned(self, p95_util: float, threshold: float = 0.8) -> bool:
        """True if p95 utilization is above the threshold (risking outages)."""
        return p95_util > threshold


@dataclass
class ScalingRecommendation:
    """Recommendation for how to scale.

    Attributes:
        strategy: "horizontal" (add instances) or "vertical" (bigger instances)
        target_instances: recommended number of instances
        estimated_cost: estimated monthly cost in USD
        headroom_months: how many months of growth this covers
    """
    strategy: str
    target_instances: int
    estimated_cost: float
    headroom_months: float


class CapacityPlanner:
    """Project future load and recommend scaling strategies.

    Uses exponential growth modeling to predict when capacity will be
    exhausted and how much to scale to maintain headroom.
    """

    def __init__(self, current_load: float, growth_rate_monthly: float):
        """
        Args:
            current_load: current traffic in RPS
            growth_rate_monthly: monthly growth rate (e.g., 0.1 for 10%)
        """
        self.current_load = current_load
        self.growth_rate = growth_rate_monthly

    def project_load(self, months_ahead: float) -> float:
        """Project traffic using exponential growth.

        load(t) = current_load * (1 + growth_rate)^t
        """
        return self.current_load * (1 + self.growth_rate) ** months_ahead

    def time_to_exhaustion(self, current_capacity: float) -> float:
        """Months until current capacity is exhausted.

        Solves: current_load * (1 + growth_rate)^t = current_capacity
        => t = log(capacity / load) / log(1 + growth_rate)

        Returns float("inf") if load is not growing or is below capacity
        with zero growth.
        """
        if self.current_load <= 0 or self.current_load >= current_capacity:
            return 0.0

        if self.growth_rate <= 0:
            return float("inf")

        return math.log(current_capacity / self.current_load) / math.log(1 + self.growth_rate)

    def recommend_scaling(
        self,
        target_headroom: float = 6.0,
        instance_capacity: float = 100.0,
        cost_per_instance_month: float = 500.0,
    ) -> ScalingRecommendation:
        """Recommend a scaling strategy to maintain headroom.

        Args:
            target_headroom: months of growth to provision for
            instance_capacity: RPS capacity per instance
            cost_per_instance_month: monthly cost per instance

        Returns:
            ScalingRecommendation with strategy, instances, cost, headroom.
        """
        future_load = self.project_load(target_headroom)

        # Add 30% buffer above projected load
        target_capacity = future_load * 1.3
        instances_needed = math.ceil(target_capacity / instance_capacity)

        # Determine strategy
        current_instances = math.ceil(self.current_load / instance_capacity)
        if instances_needed <= current_instances * 2:
            strategy = "vertical"  # can upgrade existing instances
        else:
            strategy = "horizontal"  # need more instances

        estimated_cost = instances_needed * cost_per_instance_month

        return ScalingRecommendation(
            strategy=strategy,
            target_instances=instances_needed,
            estimated_cost=round(estimated_cost, 2),
            headroom_months=target_headroom,
        )
