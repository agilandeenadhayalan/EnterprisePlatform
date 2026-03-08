"""
Dispatch service repository — database access layer.

Handles dispatch assignment CRUD and zone queries.
"""

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import DispatchAssignmentModel, DispatchZoneModel


class DispatchRepository:
    """Database operations for the dispatch service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Assignment operations ──

    async def create_assignment(
        self,
        trip_id: str,
        driver_id: str,
        score: float,
        distance_to_pickup: Optional[float] = None,
    ) -> DispatchAssignmentModel:
        """Create a new dispatch assignment."""
        assignment = DispatchAssignmentModel(
            trip_id=trip_id,
            driver_id=driver_id,
            score=score,
            distance_to_pickup=distance_to_pickup,
        )
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def get_assignment_by_id(self, assignment_id: str) -> Optional[DispatchAssignmentModel]:
        """Find an assignment by its UUID."""
        result = await self.db.execute(
            select(DispatchAssignmentModel).where(DispatchAssignmentModel.id == assignment_id)
        )
        return result.scalar_one_or_none()

    async def get_trip_assignments(self, trip_id: str) -> list[DispatchAssignmentModel]:
        """Get all assignments for a trip, ordered by score descending."""
        result = await self.db.execute(
            select(DispatchAssignmentModel)
            .where(DispatchAssignmentModel.trip_id == trip_id)
            .order_by(DispatchAssignmentModel.score.desc())
        )
        return list(result.scalars().all())

    async def update_assignment_status(
        self, assignment_id: str, status: str
    ) -> Optional[DispatchAssignmentModel]:
        """Update the status of an assignment."""
        await self.db.execute(
            update(DispatchAssignmentModel)
            .where(DispatchAssignmentModel.id == assignment_id)
            .values(status=status)
        )
        return await self.get_assignment_by_id(assignment_id)

    # ── Zone operations ──

    async def list_zones(self) -> list[DispatchZoneModel]:
        """List all dispatch zones."""
        result = await self.db.execute(
            select(DispatchZoneModel).order_by(DispatchZoneModel.name)
        )
        return list(result.scalars().all())
