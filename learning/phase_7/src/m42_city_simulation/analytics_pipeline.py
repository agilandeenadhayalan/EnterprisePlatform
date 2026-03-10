"""
Analytics pipeline — collecting and analyzing simulation metrics.

WHY THIS MATTERS:
Running a simulation without analytics is like driving with your eyes
closed. You need to measure KPIs at each tick to understand system
behavior: Are drivers utilized? Are riders waiting too long? Is supply
meeting demand? Analytics turns raw simulation output into actionable
insights for tuning dispatch, pricing, and fleet sizing.

Key concepts:
  - Per-tick metrics: snapshot of system state at each time step
  - Time series analysis: tracking metrics over time
  - KPI calculation: driver utilization, wait time, throughput
  - Scenario comparison: evaluating different configurations side-by-side
"""

from dataclasses import dataclass, field


@dataclass
class TickMetrics:
    """Metrics captured at a single simulation tick.

    Records the system state at one point in time for later analysis.
    """

    tick: int
    active_drivers: int
    active_riders: int
    pending_requests: int
    completed_trips: int
    avg_wait_ticks: float


class MetricsCollector:
    """Collect and query per-tick simulation metrics.

    Stores a time series of TickMetrics and provides windowed
    queries for analysis.
    """

    def __init__(self):
        self._metrics: list = []

    def record_tick(self, metrics: TickMetrics) -> None:
        """Store metrics for one tick."""
        self._metrics.append(metrics)

    def get_time_series(self, metric_name: str) -> list:
        """Return a list of (tick, value) tuples for a named metric.

        The metric_name must match a TickMetrics field name.
        """
        return [
            (m.tick, getattr(m, metric_name))
            for m in self._metrics
            if hasattr(m, metric_name)
        ]

    def get_window(self, start_tick: int, end_tick: int) -> list:
        """Return metrics for ticks in [start_tick, end_tick] inclusive."""
        return [
            m for m in self._metrics
            if start_tick <= m.tick <= end_tick
        ]


class KPICalculator:
    """Calculate key performance indicators from simulation metrics.

    Transforms raw per-tick data into meaningful business metrics
    that guide operational decisions.
    """

    def driver_utilization(self, metrics_list: list) -> float:
        """Calculate average driver utilization.

        Utilization = average fraction of drivers that are active
        (not idle). active_drivers / (active_drivers + idle).
        We approximate by using active_drivers / total_drivers_seen.

        For simplicity: avg(active_drivers) / max(active_drivers)
        across all ticks. Returns 0.0 if no metrics.
        """
        if not metrics_list:
            return 0.0
        total_active = sum(m.active_drivers for m in metrics_list)
        max_drivers = max(
            (m.active_drivers + m.active_riders) for m in metrics_list
        )
        if max_drivers == 0:
            return 0.0
        return total_active / (len(metrics_list) * max(1, max(m.active_drivers for m in metrics_list if m.active_drivers > 0) if any(m.active_drivers > 0 for m in metrics_list) else 1))

    def rider_wait_time(self, metrics_list: list) -> float:
        """Calculate average rider wait time in ticks.

        Simple average of avg_wait_ticks across all recorded ticks.
        """
        if not metrics_list:
            return 0.0
        total_wait = sum(m.avg_wait_ticks for m in metrics_list)
        return total_wait / len(metrics_list)

    def supply_demand_ratio(self, metrics_list: list) -> float:
        """Calculate average supply/demand ratio.

        ratio = active_drivers / pending_requests for each tick.
        Higher ratio means more supply than demand (good for riders).
        Returns float('inf') if no pending requests across all ticks.
        """
        if not metrics_list:
            return 0.0
        ratios = []
        for m in metrics_list:
            if m.pending_requests > 0:
                ratios.append(m.active_drivers / m.pending_requests)
        if not ratios:
            return float('inf')
        return sum(ratios) / len(ratios)

    def trips_per_tick(self, metrics_list: list) -> float:
        """Calculate average completed trips per tick (throughput).

        Simple average of completed_trips across all ticks.
        """
        if not metrics_list:
            return 0.0
        total_trips = sum(m.completed_trips for m in metrics_list)
        return total_trips / len(metrics_list)


class SimulationReport:
    """Generate a summary report from collected metrics.

    Wraps a MetricsCollector and KPICalculator to produce a
    comprehensive summary of a simulation run.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        self._collector = metrics_collector
        self._kpi = KPICalculator()

    def summary(self) -> dict:
        """Generate a summary dict with all KPIs.

        Returns dict with keys: driver_utilization, rider_wait_time,
        supply_demand_ratio, trips_per_tick, total_ticks.
        """
        all_metrics = self._collector._metrics
        return {
            "driver_utilization": self._kpi.driver_utilization(all_metrics),
            "rider_wait_time": self._kpi.rider_wait_time(all_metrics),
            "supply_demand_ratio": self._kpi.supply_demand_ratio(all_metrics),
            "trips_per_tick": self._kpi.trips_per_tick(all_metrics),
            "total_ticks": len(all_metrics),
        }

    def compare(self, other: "SimulationReport") -> dict:
        """Compare this report with another, side-by-side.

        Returns dict mapping KPI name -> {"self": value, "other": value}.
        """
        my_summary = self.summary()
        other_summary = other.summary()
        comparison = {}
        for key in my_summary:
            comparison[key] = {
                "self": my_summary[key],
                "other": other_summary.get(key),
            }
        return comparison


class ScenarioComparator:
    """Compare multiple simulation scenarios by KPIs.

    Stores named scenarios and provides comparison and ranking
    across all registered simulations.
    """

    def __init__(self):
        self._scenarios: dict = {}

    def add_scenario(self, name: str, report: SimulationReport) -> None:
        """Register a named scenario with its report."""
        self._scenarios[name] = report

    def compare_all(self) -> dict:
        """Generate a comparison matrix of all scenarios.

        Returns dict mapping scenario_name -> summary_dict.
        """
        return {
            name: report.summary()
            for name, report in self._scenarios.items()
        }

    def best_by(self, kpi_name: str) -> str:
        """Find the scenario with the best value for a given KPI.

        "Best" = highest value for utilization, trips_per_tick, supply_demand_ratio.
        "Best" = lowest value for rider_wait_time.

        Returns the scenario name.
        """
        lower_is_better = {"rider_wait_time"}
        summaries = self.compare_all()

        if not summaries:
            return None

        if kpi_name in lower_is_better:
            return min(
                summaries.keys(),
                key=lambda name: summaries[name].get(kpi_name, float('inf')),
            )
        else:
            return max(
                summaries.keys(),
                key=lambda name: summaries[name].get(kpi_name, float('-inf')),
            )
