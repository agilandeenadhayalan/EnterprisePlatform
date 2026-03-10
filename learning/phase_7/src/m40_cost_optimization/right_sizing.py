"""
Right-sizing analysis — matching instance capacity to actual utilization.

WHY THIS MATTERS:
Cloud over-provisioning is the #1 waste in platform engineering. Most
teams request large instances "just in case" and never revisit. A
mobility platform running hundreds of microservices can easily waste
40-60% of compute spend on idle capacity. Right-sizing analyzes actual
CPU, memory, and network usage to recommend optimal instance types,
often cutting costs 30-50% with zero performance impact.

Key concepts:
  - Utilization analysis: comparing average and p95 metrics against
    thresholds to categorize instances as over/under/right-provisioned.
  - Instance matching: finding the cheapest instance type that still
    meets p95 resource requirements with headroom.
  - Savings estimation: projecting monthly cost reduction from switching
    to recommended instance types.
"""

from dataclasses import dataclass, field


@dataclass
class InstanceMetrics:
    """Resource utilization metrics for an instance.

    Tracks both average and p95 (95th percentile) for CPU and memory.
    Average shows typical usage; p95 captures peak demand. Both are
    needed: low avg + low p95 = over-provisioned, low avg + high p95 =
    bursty (may need different instance family, not smaller).
    """

    cpu_avg: float          # 0.0 - 1.0 (fraction of total CPU)
    cpu_p95: float          # 0.0 - 1.0
    memory_avg: float       # 0.0 - 1.0 (fraction of total memory)
    memory_p95: float       # 0.0 - 1.0
    network_io_mbps: float  # average network throughput


@dataclass
class InstanceType:
    """An available cloud instance type with its specs and cost.

    Represents a specific VM offering (e.g., m5.large) with its
    resource capacity and hourly cost.
    """

    name: str
    vcpus: int
    memory_gb: float
    cost_per_hour: float


class UtilizationAnalyzer:
    """Categorize instances based on their utilization metrics.

    Uses configurable thresholds to determine if an instance is
    over-provisioned (wasting money), right-sized (optimal), or
    under-provisioned (performance risk).
    """

    def analyze(self, metrics: InstanceMetrics) -> str:
        """Categorize utilization as over_provisioned, right_sized, or under_provisioned.

        Logic:
          - over_provisioned: both avg CPU and avg memory below 30%
          - under_provisioned: p95 CPU or p95 memory above 80%
          - right_sized: everything else
        """
        if self.is_over_provisioned(metrics):
            return "over_provisioned"
        if self.is_under_provisioned(metrics):
            return "under_provisioned"
        return "right_sized"

    def is_over_provisioned(self, metrics: InstanceMetrics, threshold: float = 0.3) -> bool:
        """Check if instance is over-provisioned.

        Both average CPU and average memory must be below the threshold.
        This means the instance consistently uses less than 30% of its
        capacity — a strong signal it can be downsized.
        """
        return metrics.cpu_avg < threshold and metrics.memory_avg < threshold

    def is_under_provisioned(self, metrics: InstanceMetrics, threshold: float = 0.8) -> bool:
        """Check if instance is under-provisioned.

        Either p95 CPU or p95 memory exceeds the threshold, meaning the
        instance regularly hits its capacity limits. This is a performance
        risk — the instance should be upsized or the workload redistributed.
        """
        return metrics.cpu_p95 > threshold or metrics.memory_p95 > threshold


class RightSizer:
    """Recommend optimal instance types based on utilization data.

    Given an instance's current metrics and a catalog of available
    instance types, recommends the cheapest option that still meets
    resource requirements with headroom.
    """

    def __init__(self, available_instances: list):
        """Initialize with a list of available InstanceType options."""
        self._instances = sorted(available_instances, key=lambda i: i.cost_per_hour)

    def recommend(self, current_instance: InstanceType, metrics: InstanceMetrics) -> InstanceType:
        """Suggest the optimal instance type for this workload.

        Finds the cheapest instance that provides enough vCPUs and memory
        to handle the p95 workload with 20% headroom. If no smaller
        instance fits, returns the current instance.

        The required resources are estimated from the current instance's
        specs scaled by p95 utilization plus headroom.
        """
        required_vcpus = current_instance.vcpus * metrics.cpu_p95 * 1.2
        required_memory = current_instance.memory_gb * metrics.memory_p95 * 1.2

        for inst in self._instances:
            if inst.vcpus >= required_vcpus and inst.memory_gb >= required_memory:
                return inst

        # No suitable smaller instance — keep current
        return current_instance

    def calculate_savings(self, current: InstanceType, recommended: InstanceType) -> float:
        """Calculate estimated monthly savings from switching instances.

        Monthly = hourly_delta * 24 hours * 30 days.
        Returns 0.0 if recommended is more expensive (no savings).
        """
        hourly_delta = current.cost_per_hour - recommended.cost_per_hour
        if hourly_delta <= 0:
            return 0.0
        return hourly_delta * 24 * 30


@dataclass
class RightSizingReport:
    """Report summarizing a right-sizing recommendation.

    Contains the current instance, recommended instance, projected
    monthly savings, and a confidence score based on data quality.
    """

    current_instance: InstanceType
    recommended_instance: InstanceType
    monthly_savings: float
    confidence: float  # 0.0 - 1.0
