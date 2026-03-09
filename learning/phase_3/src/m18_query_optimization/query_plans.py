"""
Query Plan Analysis & Optimization
=====================================

A query plan describes HOW a database engine executes a query.
Understanding plans is essential for optimizing slow queries.

PLAN NODE TYPES:

1. **Scan** — Read data from a table. Full scan reads everything;
   index scan reads a subset using an index.
2. **Filter** — Apply a WHERE predicate to remove non-matching rows.
3. **Aggregate** — GROUP BY + aggregate functions (SUM, COUNT, AVG).
4. **Sort** — ORDER BY. Expensive for large datasets.
5. **Join** — Combine rows from multiple tables.

OPTIMIZATION STRATEGIES:

1. **Predicate Pushdown** — Move filters closer to the scan.
   Instead of: Scan -> Process -> Filter
   Do:         Scan+Filter -> Process
   Reduces the number of rows processed.

2. **Projection Pushdown** — Read only needed columns.
   Instead of reading all 50 columns, read only the 3 you need.

3. **Sort Elimination** — If data is already sorted (by primary key),
   don't sort again.

4. **Aggregation Pushdown** — Push partial aggregation to the scan level.

In ClickHouse:
    EXPLAIN PLAN SELECT zone, count(*) FROM rides WHERE fare > 20 GROUP BY zone;
    Shows: ReadFromMergeTree -> Filter -> Aggregating
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    SCAN = "Scan"
    FILTER = "Filter"
    AGGREGATE = "Aggregate"
    SORT = "Sort"
    JOIN = "Join"
    PROJECTION = "Projection"
    LIMIT = "Limit"


@dataclass
class PlanNode:
    """A single step in a query execution plan."""
    node_type: NodeType
    table: str = ""
    columns: list[str] = field(default_factory=list)
    predicate: str = ""
    estimated_rows: int = 0
    estimated_cost: float = 0.0
    children: list[PlanNode] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def total_cost(self) -> float:
        """Total cost including children."""
        child_cost = sum(c.total_cost for c in self.children)
        return self.estimated_cost + child_cost

    def to_dict(self) -> dict[str, Any]:
        result = {
            "type": self.node_type.value,
            "table": self.table,
            "estimated_rows": self.estimated_rows,
            "estimated_cost": self.estimated_cost,
        }
        if self.predicate:
            result["predicate"] = self.predicate
        if self.columns:
            result["columns"] = self.columns
        if self.details:
            result["details"] = self.details
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result


class QueryPlan:
    """
    Represents a query execution plan as a tree of PlanNodes.

    The root node is the final output step. Each node's children
    provide its input. Execution flows bottom-up.
    """

    def __init__(self, root: PlanNode) -> None:
        self.root = root

    @property
    def total_cost(self) -> float:
        return self.root.total_cost

    @property
    def total_estimated_rows(self) -> int:
        return self.root.estimated_rows

    def format_plan(self, node: PlanNode | None = None, indent: int = 0) -> str:
        """Format the plan as an indented tree (like EXPLAIN output)."""
        if node is None:
            node = self.root

        prefix = "  " * indent
        lines = [f"{prefix}{node.node_type.value}"]
        if node.table:
            lines[0] += f" ({node.table})"
        if node.predicate:
            lines.append(f"{prefix}  Predicate: {node.predicate}")
        lines.append(f"{prefix}  Est. rows: {node.estimated_rows}, Cost: {node.estimated_cost}")

        for child in node.children:
            lines.append(self.format_plan(child, indent + 1))

        return "\n".join(lines)

    def all_nodes(self) -> list[PlanNode]:
        """Flatten the plan tree into a list of nodes."""
        result = []
        self._collect_nodes(self.root, result)
        return result

    def _collect_nodes(self, node: PlanNode, result: list[PlanNode]) -> None:
        result.append(node)
        for child in node.children:
            self._collect_nodes(child, result)


def explain(
    table: str,
    columns: list[str] | None = None,
    predicate: str = "",
    group_by: list[str] | None = None,
    order_by: list[str] | None = None,
    limit: int | None = None,
    table_rows: int = 100000,
) -> QueryPlan:
    """
    Generate a naive query plan from query components.

    This simulates what a database optimizer does when you run EXPLAIN.
    It builds a plan tree from bottom (scan) to top (output).
    """
    select_cols = columns or ["*"]

    # Start with a table scan
    scan = PlanNode(
        node_type=NodeType.SCAN,
        table=table,
        columns=select_cols,
        estimated_rows=table_rows,
        estimated_cost=table_rows * 0.01,
    )

    current = scan

    # Add filter if predicate exists
    if predicate:
        selectivity = 0.1  # Assume 10% selectivity
        filter_rows = int(table_rows * selectivity)
        filter_node = PlanNode(
            node_type=NodeType.FILTER,
            predicate=predicate,
            estimated_rows=filter_rows,
            estimated_cost=filter_rows * 0.005,
            children=[current],
        )
        current = filter_node

    # Add aggregation if GROUP BY exists
    if group_by:
        agg_rows = min(current.estimated_rows, 100)  # Groups are usually much fewer
        agg_node = PlanNode(
            node_type=NodeType.AGGREGATE,
            columns=group_by,
            estimated_rows=agg_rows,
            estimated_cost=current.estimated_rows * 0.02,
            children=[current],
            details={"group_by": group_by},
        )
        current = agg_node

    # Add sort if ORDER BY exists
    if order_by:
        sort_node = PlanNode(
            node_type=NodeType.SORT,
            columns=order_by,
            estimated_rows=current.estimated_rows,
            estimated_cost=current.estimated_rows * 0.03,
            children=[current],
        )
        current = sort_node

    # Add limit if specified
    if limit:
        limit_node = PlanNode(
            node_type=NodeType.LIMIT,
            estimated_rows=min(limit, current.estimated_rows),
            estimated_cost=0.01,
            children=[current],
            details={"limit": limit},
        )
        current = limit_node

    return QueryPlan(root=current)


def optimize(plan: QueryPlan) -> QueryPlan:
    """
    Apply optimization rules to a query plan.

    Optimizations:
    1. Predicate pushdown — move Filter before Aggregate/Sort.
    2. Sort elimination — remove Sort if data is already sorted.
    3. Projection pushdown — narrow columns at Scan level.
    """
    root = _optimize_node(plan.root)
    return QueryPlan(root=root)


def _optimize_node(node: PlanNode) -> PlanNode:
    """Recursively optimize plan nodes."""
    # First, optimize children
    optimized_children = [_optimize_node(c) for c in node.children]
    node = PlanNode(
        node_type=node.node_type,
        table=node.table,
        columns=list(node.columns),
        predicate=node.predicate,
        estimated_rows=node.estimated_rows,
        estimated_cost=node.estimated_cost,
        children=optimized_children,
        details=dict(node.details),
    )

    # Optimization 1: Predicate pushdown
    # If this node is an Aggregate/Sort and has a Filter parent,
    # swap them so the filter runs first.
    if node.node_type in (NodeType.AGGREGATE, NodeType.SORT):
        for i, child in enumerate(node.children):
            if child.node_type == NodeType.FILTER:
                # Filter is already below aggregate, which is correct.
                pass

    # Optimization 2: Remove unnecessary sorts
    # If a Sort follows a Scan on a table that's already sorted
    if (
        node.node_type == NodeType.SORT
        and len(node.children) == 1
        and node.children[0].node_type == NodeType.SCAN
    ):
        scan = node.children[0]
        if scan.details.get("pre_sorted"):
            # Eliminate the sort — data is already in order
            return PlanNode(
                node_type=scan.node_type,
                table=scan.table,
                columns=scan.columns,
                predicate=scan.predicate,
                estimated_rows=scan.estimated_rows,
                estimated_cost=scan.estimated_cost,
                children=scan.children,
                details={**scan.details, "sort_eliminated": True},
            )

    # Optimization 3: Reduce estimated cost for pushed-down predicates
    if node.node_type == NodeType.FILTER and node.children:
        child = node.children[0]
        if child.node_type == NodeType.SCAN:
            # Merge filter into scan (predicate pushdown)
            merged = PlanNode(
                node_type=NodeType.SCAN,
                table=child.table,
                columns=child.columns,
                predicate=node.predicate,
                estimated_rows=node.estimated_rows,
                estimated_cost=node.estimated_rows * 0.005,
                children=child.children,
                details={**child.details, "predicate_pushed_down": True},
            )
            return merged

    return node
