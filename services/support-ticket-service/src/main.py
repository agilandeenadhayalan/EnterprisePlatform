"""
Support Ticket Service — FastAPI application.

ROUTES:
  POST  /tickets              — Create a new support ticket
  GET   /tickets/{id}         — Get a ticket by ID
  GET   /users/{id}/tickets   — Get all tickets for a user
  PATCH /tickets/{id}/status  — Update ticket status
  GET   /tickets              — List all tickets (admin)
  GET   /health               — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found

import config as service_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(service_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="Support Ticket Service",
    version="0.1.0",
    description="Customer support ticket management for Smart Mobility Platform",
    lifespan=lifespan,
)


def _ticket_to_response(t) -> schemas.TicketResponse:
    """Convert a TicketModel to a TicketResponse schema."""
    return schemas.TicketResponse(
        id=str(t.id),
        user_id=str(t.user_id),
        subject=t.subject,
        description=t.description,
        category=t.category,
        priority=t.priority,
        status=t.status,
        assigned_to=str(t.assigned_to) if t.assigned_to else None,
        resolved_at=t.resolved_at,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# ── Routes ──


@app.post("/tickets", response_model=schemas.TicketResponse, status_code=201)
async def create_ticket(
    body: schemas.CreateTicketRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new support ticket."""
    repo = repository.TicketRepository(db)
    ticket = await repo.create_ticket(
        user_id=body.user_id,
        subject=body.subject,
        description=body.description,
        category=body.category,
        priority=body.priority,
    )
    return _ticket_to_response(ticket)


@app.get("/tickets/{ticket_id}", response_model=schemas.TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a support ticket by ID."""
    repo = repository.TicketRepository(db)
    ticket = await repo.get_ticket(ticket_id)
    if not ticket:
        raise not_found("Support ticket", ticket_id)
    return _ticket_to_response(ticket)


@app.get("/users/{user_id}/tickets", response_model=schemas.TicketListResponse)
async def get_user_tickets(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all support tickets for a user."""
    repo = repository.TicketRepository(db)
    tickets = await repo.get_user_tickets(user_id)
    return schemas.TicketListResponse(
        tickets=[_ticket_to_response(t) for t in tickets],
        count=len(tickets),
    )


@app.patch("/tickets/{ticket_id}/status", response_model=schemas.TicketResponse)
async def update_ticket_status(
    ticket_id: str,
    body: schemas.UpdateTicketStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update ticket status (and optionally assign to an agent)."""
    repo = repository.TicketRepository(db)
    ticket = await repo.update_status(
        ticket_id=ticket_id,
        status=body.status,
        assigned_to=body.assigned_to,
    )
    if not ticket:
        raise not_found("Support ticket", ticket_id)
    return _ticket_to_response(ticket)


@app.get("/tickets", response_model=schemas.TicketListResponse)
async def list_tickets(
    status: str = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """List all support tickets (admin view)."""
    repo = repository.TicketRepository(db)
    tickets = await repo.list_tickets(status=status)
    return schemas.TicketListResponse(
        tickets=[_ticket_to_response(t) for t in tickets],
        count=len(tickets),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
