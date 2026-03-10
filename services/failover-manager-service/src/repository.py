"""
Failover Manager repository — in-memory failover events and region health storage.

Manages failover events, triggers, and region health tracking.
"""

import uuid
from datetime import datetime
from typing import Optional

from models import FailoverEvent, RegionHealth


class FailoverRepository:
    """In-memory failover events and region health storage."""

    def __init__(self):
        self._events: dict[str, FailoverEvent] = {}
        self._health: dict[str, RegionHealth] = {}  # region_code -> health
        self._primary_region: Optional[str] = None

    # ── Event CRUD ──

    def create_event(
        self,
        source_region: str,
        target_region: str,
        trigger_type: str = "manual",
        reason: str = "",
        status: str = "initiated",
    ) -> FailoverEvent:
        """Record a failover event."""
        event_id = str(uuid.uuid4())
        event = FailoverEvent(
            id=event_id,
            source_region=source_region,
            target_region=target_region,
            trigger_type=trigger_type,
            reason=reason,
            status=status,
        )
        self._events[event_id] = event
        # Ensure health entries exist
        for code in [source_region, target_region]:
            if code not in self._health:
                self._health[code] = RegionHealth(region_code=code)
        return event

    def get_event(self, event_id: str) -> Optional[FailoverEvent]:
        """Get a failover event by ID."""
        return self._events.get(event_id)

    def list_events(self) -> list[FailoverEvent]:
        """List all failover events."""
        return list(self._events.values())

    # ── Failover trigger ──

    def trigger_failover(
        self,
        source_region: str,
        target_region: str,
        reason: str = "",
    ) -> FailoverEvent:
        """Trigger a failover from source to target region."""
        event = self.create_event(
            source_region=source_region,
            target_region=target_region,
            trigger_type="manual",
            reason=reason,
            status="in_progress",
        )
        # Mark source as failing
        if source_region in self._health:
            self._health[source_region].status = "failing"
            self._health[source_region].consecutive_failures += 1
        else:
            self._health[source_region] = RegionHealth(
                region_code=source_region, status="failing", consecutive_failures=1,
            )
        # Mark target as healthy
        if target_region not in self._health:
            self._health[target_region] = RegionHealth(region_code=target_region)
        # Complete the failover
        event.status = "completed"
        event.completed_at = datetime.utcnow()
        # Promote target
        self._primary_region = target_region
        return event

    # ── Promote ──

    def promote_region(self, region_code: str) -> Optional[RegionHealth]:
        """Promote a region to primary."""
        if region_code not in self._health:
            self._health[region_code] = RegionHealth(region_code=region_code)
        self._health[region_code].status = "healthy"
        self._primary_region = region_code
        return self._health[region_code]

    # ── Health ──

    def get_health(self, region_code: str) -> Optional[RegionHealth]:
        """Get health for a region."""
        return self._health.get(region_code)

    def list_health(self) -> list[RegionHealth]:
        """List health for all regions."""
        return list(self._health.values())

    def get_failover_status(self) -> list[dict]:
        """Get failover status for all tracked regions."""
        result = []
        for code, health in self._health.items():
            active = sum(
                1 for e in self._events.values()
                if (e.source_region == code or e.target_region == code)
                and e.status in ("initiated", "in_progress")
            )
            result.append({
                "region_code": code,
                "health_status": health.status,
                "active_failovers": active,
                "is_primary": code == self._primary_region,
            })
        return result


# Singleton repository instance
repo = FailoverRepository()
