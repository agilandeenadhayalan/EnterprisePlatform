"""
Domain models for the Demand Simulator service.
"""


class DemandScenario:
    """A demand simulation scenario."""

    def __init__(
        self,
        id: str,
        name: str,
        pattern_type: str,
        parameters: dict,
        duration_hours: int,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.name = name
        self.pattern_type = pattern_type
        self.parameters = parameters
        self.duration_hours = duration_hours
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "pattern_type": self.pattern_type,
            "parameters": self.parameters,
            "duration_hours": self.duration_hours,
            "created_at": self.created_at,
        }


class SimulationRun:
    """A simulation run result."""

    def __init__(
        self,
        id: str,
        scenario_id: str,
        status: str,
        generated_events: int,
        results: dict,
        started_at: str,
        completed_at: str | None = None,
    ):
        self.id = id
        self.scenario_id = scenario_id
        self.status = status
        self.generated_events = generated_events
        self.results = results
        self.started_at = started_at
        self.completed_at = completed_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "status": self.status,
            "generated_events": self.generated_events,
            "results": self.results,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class DemandEvent:
    """A generated demand event."""

    def __init__(
        self,
        timestamp: str,
        zone_id: str,
        demand_level: float,
        pattern_source: str,
    ):
        self.timestamp = timestamp
        self.zone_id = zone_id
        self.demand_level = demand_level
        self.pattern_source = pattern_source

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "zone_id": self.zone_id,
            "demand_level": self.demand_level,
            "pattern_source": self.pattern_source,
        }
