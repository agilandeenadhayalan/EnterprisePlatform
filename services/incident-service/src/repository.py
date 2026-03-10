"""
Incident repository — in-memory incident storage.

Manages incident lifecycle: reporting, investigation, resolution.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import Incident, IncidentSeverity, IncidentStatus


class IncidentRepository:
    """In-memory incident storage."""

    def __init__(self):
        self._incidents: dict[str, Incident] = {}

    # ── Incident CRUD ──

    def create_incident(
        self,
        type: str,
        severity: str,
        description: str,
        reported_by: Optional[str] = None,
        location: Optional[dict[str, Any]] = None,
    ) -> Incident:
        """Report a new incident."""
        incident_id = str(uuid.uuid4())
        incident = Incident(
            id=incident_id,
            type=type,
            severity=severity,
            description=description,
            reported_by=reported_by,
            location=location,
        )
        self._incidents[incident_id] = incident
        return incident

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get an incident by ID."""
        return self._incidents.get(incident_id)

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> list[Incident]:
        """List all incidents, optionally filtered."""
        incidents = list(self._incidents.values())
        if status:
            incidents = [i for i in incidents if i.status == status]
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        return incidents

    def update_incident(self, incident_id: str, **fields) -> Optional[Incident]:
        """Update specific fields on an incident."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(incident, key):
                setattr(incident, key, value)
        return incident

    # ── Investigation ──

    def investigate(self, incident_id: str) -> Optional[Incident]:
        """Begin investigation on an incident."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        incident.status = "investigating"
        return incident

    def add_note(
        self,
        incident_id: str,
        author: str,
        content: str,
    ) -> Optional[dict]:
        """Add an investigation note to an incident."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        note = {
            "author": author,
            "content": content,
            "added_at": datetime.utcnow().isoformat(),
        }
        incident.investigation_notes.append(note)
        return note

    def resolve(self, incident_id: str, resolution: str) -> Optional[Incident]:
        """Resolve an incident."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        incident.status = "resolved"
        incident.resolved_at = datetime.utcnow()
        incident.resolution = resolution
        return incident

    # ── Statistics ──

    def get_stats(self) -> dict:
        """Get incident statistics."""
        incidents = list(self._incidents.values())
        total = len(incidents)

        by_severity = {}
        for sev in IncidentSeverity:
            count = len([i for i in incidents if i.severity == sev.value])
            if count > 0:
                by_severity[sev.value] = count

        by_status = {}
        for st in IncidentStatus:
            count = len([i for i in incidents if i.status == st.value])
            if count > 0:
                by_status[st.value] = count

        # Calculate average resolution time
        resolved = [i for i in incidents if i.resolved_at and i.reported_at]
        avg_hours = None
        if resolved:
            total_hours = sum(
                (i.resolved_at - i.reported_at).total_seconds() / 3600
                for i in resolved
            )
            avg_hours = round(total_hours / len(resolved), 2)

        return {
            "total": total,
            "by_severity": by_severity,
            "by_status": by_status,
            "avg_resolution_hours": avg_hours,
        }


# Singleton repository instance
repo = IncidentRepository()
