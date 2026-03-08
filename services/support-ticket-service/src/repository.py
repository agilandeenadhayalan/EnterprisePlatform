"""
Support ticket service repository — database access layer.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import SupportTicketModel


class TicketRepository:
    """Database operations for the support ticket service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_ticket(
        self,
        user_id: str,
        subject: str,
        description: str,
        category: str = "general",
        priority: str = "medium",
    ) -> SupportTicketModel:
        """Create a new support ticket."""
        ticket = SupportTicketModel(
            user_id=user_id,
            subject=subject,
            description=description,
            category=category,
            priority=priority,
        )
        self.db.add(ticket)
        await self.db.flush()
        return ticket

    async def get_ticket(self, ticket_id: str) -> Optional[SupportTicketModel]:
        """Get a ticket by ID."""
        result = await self.db.execute(
            select(SupportTicketModel).where(SupportTicketModel.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def get_user_tickets(self, user_id: str, limit: int = 50) -> List[SupportTicketModel]:
        """Get all tickets for a user."""
        result = await self.db.execute(
            select(SupportTicketModel)
            .where(SupportTicketModel.user_id == user_id)
            .order_by(SupportTicketModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        ticket_id: str,
        status: str,
        assigned_to: Optional[str] = None,
    ) -> Optional[SupportTicketModel]:
        """Update ticket status and optionally assign to an agent."""
        now = datetime.now(timezone.utc)
        values = {"status": status, "updated_at": now}
        if assigned_to:
            values["assigned_to"] = assigned_to
        if status == "resolved":
            values["resolved_at"] = now
        await self.db.execute(
            update(SupportTicketModel)
            .where(SupportTicketModel.id == ticket_id)
            .values(**values)
        )
        return await self.get_ticket(ticket_id)

    async def list_tickets(self, limit: int = 50, status: Optional[str] = None) -> List[SupportTicketModel]:
        """List all tickets (admin view) with optional status filter."""
        query = select(SupportTicketModel).order_by(SupportTicketModel.created_at.desc()).limit(limit)
        if status:
            query = query.where(SupportTicketModel.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())
