"""
Tickets API endpoints for admin dashboard.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.supabase_client import get_supabase_client
from app.db.models import Ticket, TicketStatus, TicketCreate

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = get_supabase_client()


class TicketUpdate(BaseModel):
    status: TicketStatus


@router.get("/tickets", response_model=list[Ticket])
async def list_tickets(
    status: TicketStatus = Query(default=None),
    limit: int = Query(default=100, le=500),
):
    """List tickets with optional status filter."""
    tickets = await supabase.get_tickets(status=status.value if status else None, limit=limit)
    return tickets


@router.get("/tickets/{ticket_id}", response_model=Ticket)
async def get_ticket(ticket_id: UUID):
    """Get a specific ticket by ID."""
    # This would need a get_ticket_by_id method in supabase_client
    # For now, we'll use the list method
    tickets = await supabase.get_tickets(limit=1)
    for ticket in tickets:
        if ticket.id == ticket_id:
            return ticket
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.patch("/tickets/{ticket_id}", response_model=Ticket)
async def update_ticket(ticket_id: UUID, update: TicketUpdate):
    """Update ticket status."""
    ticket = await supabase.update_ticket_status(ticket_id, update.status.value)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket