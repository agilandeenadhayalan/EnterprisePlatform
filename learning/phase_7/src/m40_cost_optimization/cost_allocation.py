"""
Cost allocation and chargeback — attributing shared costs to teams.

WHY THIS MATTERS:
In a shared platform, infrastructure costs must be allocated to the
teams and services that consume them. Without cost allocation, there's
no accountability — teams over-provision because they don't see the
bill. Chargeback (or showback) creates cost awareness, driving teams
to optimize their own usage.

Key concepts:
  - Cost tagging: labeling resources with team, environment, service
  - Allocation strategies: proportional (by usage), fixed (equal split),
    usage-based (by actual consumption metrics)
  - Cost reporting: grouping costs by service, resource type, or tag
  - Chargeback: billing teams for their share of shared resources
"""

from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


@dataclass
class CostTag:
    """A key-value tag for cost attribution.

    Tags are attached to cloud resources to track ownership and purpose.
    Examples: team=platform, env=production, service=dispatch.
    """

    key: str
    value: str


class AllocationRule(Enum):
    """How to split shared costs among consumers.

    PROPORTIONAL: split by each consumer's share of total usage.
    FIXED: equal split among all consumers.
    USAGE_BASED: split by actual metered usage.
    """

    PROPORTIONAL = "proportional"
    FIXED = "fixed"
    USAGE_BASED = "usage_based"


class CostAllocator:
    """Allocate shared infrastructure costs to consumers.

    Supports three allocation strategies for splitting costs:
    proportional (by relative usage weight), fixed (equal split),
    and usage-based (by actual metered consumption).
    """

    def __init__(self):
        self._shared_costs: list = []

    def add_shared_cost(self, name: str, amount: float, tags: list) -> None:
        """Register a shared cost with its tags.

        Args:
            name: cost item name (e.g., "Kubernetes cluster")
            amount: total cost amount
            tags: list of CostTag for attribution
        """
        self._shared_costs.append({
            "name": name,
            "amount": amount,
            "tags": tags,
        })

    def allocate_proportional(self, cost: float, consumers: dict) -> dict:
        """Split cost proportionally by usage weight.

        Args:
            cost: total cost to allocate
            consumers: dict mapping consumer_name -> usage_weight
                       e.g., {"dispatch": 60, "pricing": 40}

        Returns:
            dict mapping consumer_name -> allocated_amount
        """
        total_weight = sum(consumers.values())
        if total_weight == 0:
            return {name: 0.0 for name in consumers}
        return {
            name: cost * weight / total_weight
            for name, weight in consumers.items()
        }

    def allocate_fixed(self, cost: float, consumers: list) -> dict:
        """Split cost equally among consumers.

        Args:
            cost: total cost to allocate
            consumers: list of consumer names

        Returns:
            dict mapping consumer_name -> equal_share
        """
        if not consumers:
            return {}
        share = cost / len(consumers)
        return {name: share for name in consumers}

    def allocate_usage_based(self, cost: float, usage: dict) -> dict:
        """Split cost by actual metered usage.

        Identical to proportional but conceptually different — the weights
        are actual usage units (CPU-hours, GB-months, requests) rather
        than arbitrary weights.

        Args:
            cost: total cost to allocate
            usage: dict mapping consumer_name -> usage_amount

        Returns:
            dict mapping consumer_name -> allocated_amount
        """
        return self.allocate_proportional(cost, usage)


class CostReport:
    """Aggregate cost allocations for reporting.

    Collects individual cost allocations and provides views grouped
    by service, resource type, or custom tags.
    """

    def __init__(self):
        self._allocations: list = []

    def add_allocation(self, service: str, resource_type: str, amount: float, tags: list) -> None:
        """Record a cost allocation.

        Args:
            service: service name (e.g., "dispatch")
            resource_type: resource category (e.g., "compute", "storage")
            amount: cost amount
            tags: list of CostTag for this allocation
        """
        self._allocations.append({
            "service": service,
            "resource_type": resource_type,
            "amount": amount,
            "tags": tags,
        })

    def by_service(self) -> dict:
        """Group total costs by service.

        Returns dict mapping service_name -> total_amount.
        """
        result = defaultdict(float)
        for alloc in self._allocations:
            result[alloc["service"]] += alloc["amount"]
        return dict(result)

    def by_resource_type(self) -> dict:
        """Group total costs by resource type.

        Returns dict mapping resource_type -> total_amount.
        """
        result = defaultdict(float)
        for alloc in self._allocations:
            result[alloc["resource_type"]] += alloc["amount"]
        return dict(result)

    def by_tag(self, tag_key: str) -> dict:
        """Group total costs by a specific tag key's values.

        Returns dict mapping tag_value -> total_amount.
        Only includes allocations that have the specified tag key.
        """
        result = defaultdict(float)
        for alloc in self._allocations:
            for tag in alloc["tags"]:
                if tag.key == tag_key:
                    result[tag.value] += alloc["amount"]
        return dict(result)

    def total(self) -> float:
        """Total cost across all allocations."""
        return sum(alloc["amount"] for alloc in self._allocations)


class ChargebackCalculator:
    """Calculate per-team chargeback from a cost report.

    Maps services to teams and aggregates costs at the team level
    for internal billing.
    """

    def calculate(self, report: CostReport, team_mapping: dict) -> dict:
        """Calculate chargeback amounts per team.

        Args:
            report: CostReport with all allocations
            team_mapping: dict mapping service_name -> team_name
                          e.g., {"dispatch": "platform", "pricing": "revenue"}

        Returns:
            dict mapping team_name -> total_chargeback_amount
        """
        service_costs = report.by_service()
        team_costs = defaultdict(float)
        for service, amount in service_costs.items():
            team = team_mapping.get(service, "unassigned")
            team_costs[team] += amount
        return dict(team_costs)
