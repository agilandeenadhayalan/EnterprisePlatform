"""
In-memory demand simulator repository with pre-seeded data.
"""

import uuid
import random
from datetime import datetime, timezone

from models import DemandScenario, SimulationRun, DemandEvent


class DemandSimulatorRepository:
    """In-memory store for scenarios, runs, and demand events."""

    def __init__(self, seed: bool = False):
        self.scenarios: dict[str, DemandScenario] = {}
        self.runs: list[SimulationRun] = []
        self.events: dict[str, list[DemandEvent]] = {}  # run_id -> events
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        scenarios = [
            DemandScenario("scenario-001", "commute_morning", "commute", {"peak_hour": 8, "zones": ["zone-001", "zone-002"], "multiplier": 2.5}, 3, now),
            DemandScenario("scenario-002", "commute_evening", "commute", {"peak_hour": 18, "zones": ["zone-001", "zone-003"], "multiplier": 2.2}, 3, now),
            DemandScenario("scenario-003", "event_concert", "event", {"venue_zone": "zone-005", "capacity": 20000, "start_hour": 20}, 4, now),
            DemandScenario("scenario-004", "weather_rain", "weather", {"condition": "rain", "impact_factor": 0.7, "affected_zones": ["zone-001", "zone-002", "zone-003"]}, 6, now),
            DemandScenario("scenario-005", "surge_test", "surge", {"surge_multiplier": 3.0, "zone": "zone-001", "duration_minutes": 30}, 1, now),
        ]
        for s in scenarios:
            self.scenarios[s.id] = s

        runs = [
            SimulationRun("run-001", "scenario-001", "completed", 150, {"avg_demand": 85.0, "peak_demand": 200.0}, now, now),
            SimulationRun("run-002", "scenario-003", "completed", 200, {"avg_demand": 120.0, "peak_demand": 350.0}, now, now),
            SimulationRun("run-003", "scenario-002", "running", 75, {}, now, None),
            SimulationRun("run-004", "scenario-004", "failed", 0, {"error": "timeout"}, now, now),
        ]
        self.runs.extend(runs)

        # Generate events for completed runs
        for run in runs:
            if run.status == "completed":
                events = []
                for i in range(run.generated_events):
                    events.append(DemandEvent(
                        now,
                        f"zone-{(i % 5) + 1:03d}",
                        round(random.uniform(10.0, 200.0), 2),
                        run.scenario_id,
                    ))
                self.events[run.id] = events

    # ── Scenarios ──

    def create_scenario(self, data: dict) -> DemandScenario:
        sc_id = f"scenario-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        sc = DemandScenario(
            id=sc_id,
            name=data["name"],
            pattern_type=data["pattern_type"],
            parameters=data.get("parameters", {}),
            duration_hours=data.get("duration_hours", 1),
            created_at=now,
        )
        self.scenarios[sc.id] = sc
        return sc

    def list_scenarios(self, pattern_type: str | None = None) -> list[DemandScenario]:
        result = list(self.scenarios.values())
        if pattern_type:
            result = [s for s in result if s.pattern_type == pattern_type]
        return result

    def get_scenario(self, sc_id: str) -> DemandScenario | None:
        return self.scenarios.get(sc_id)

    # ── Runs ──

    def run_simulation(self, scenario_id: str) -> SimulationRun | None:
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            return None

        run_id = f"run-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        # Generate events based on pattern_type
        num_events = scenario.duration_hours * 10
        events = []
        for i in range(num_events):
            demand = round(random.uniform(20.0, 150.0), 2)
            events.append(DemandEvent(now, f"zone-{(i % 5) + 1:03d}", demand, scenario.id))

        avg_demand = sum(e.demand_level for e in events) / len(events) if events else 0
        peak_demand = max(e.demand_level for e in events) if events else 0

        run = SimulationRun(
            id=run_id,
            scenario_id=scenario_id,
            status="completed",
            generated_events=num_events,
            results={"avg_demand": round(avg_demand, 2), "peak_demand": round(peak_demand, 2)},
            started_at=now,
            completed_at=now,
        )
        self.runs.append(run)
        self.events[run_id] = events
        return run

    def list_runs(self, status: str | None = None) -> list[SimulationRun]:
        result = list(self.runs)
        if status:
            result = [r for r in result if r.status == status]
        return result

    def get_run(self, run_id: str) -> SimulationRun | None:
        for r in self.runs:
            if r.id == run_id:
                return r
        return None

    def get_run_events(self, run_id: str) -> list[DemandEvent]:
        return self.events.get(run_id, [])

    # ── Stats ──

    def get_stats(self) -> dict:
        by_status: dict[str, int] = {}
        total_events = 0
        for r in self.runs:
            by_status[r.status] = by_status.get(r.status, 0) + 1
            total_events += r.generated_events
        avg_events = total_events / len(self.runs) if self.runs else 0.0
        return {
            "total_scenarios": len(self.scenarios),
            "total_runs": len(self.runs),
            "by_status": by_status,
            "avg_events": round(avg_events, 2),
        }


REPO_CLASS = DemandSimulatorRepository
repo = DemandSimulatorRepository(seed=True)
