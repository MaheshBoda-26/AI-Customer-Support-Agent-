"""
Supabase client wrapper with database operations.
"""
import logging
from typing import List, Optional
from uuid import UUID

from supabase import create_client, Client

from app.core.config import settings
from app.db.models import (
    Customer, CustomerCreate,
    Conversation, ConversationCreate,
    Message, MessageCreate,
    Ticket, TicketCreate,
    Handoff, HandoffCreate,
    ConversationStatus,
)

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Wrapper for Supabase database operations."""

    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )

    # Customer operations
    async def get_or_create_customer(
        self,
        email: str,
        name: Optional[str] = None,
    ) -> Customer:
        """Get existing customer or create new one."""
        # Try to find existing customer
        result = self.client.table("customers").select("*").eq("email", email).execute()
        if result.data:
            return Customer(**result.data[0])

        # Create new customer
        customer_data = CustomerCreate(email=email, name=name).model_dump()
        result = self.client.table("customers").insert(customer_data).execute()
        return Customer(**result.data[0])

    # Conversation operations
    async def create_conversation(
        self,
        conversation: ConversationCreate,
    ) -> Conversation:
        """Create a new conversation."""
        data = conversation.model_dump(exclude_none=True)
        result = self.client.table("conversations").insert(data).execute()
        return Conversation(**result.data[0])

    async def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation by ID."""
        result = self.client.table("conversations").select("*").eq("id", str(conversation_id)).execute()
        if result.data:
            return Conversation(**result.data[0])
        return None

    async def update_conversation_status(
        self,
        conversation_id: UUID,
        status: ConversationStatus,
    ) -> Optional[Conversation]:
        """Update conversation status."""
        result = (
            self.client.table("conversations")
            .update({"status": status.value})
            .eq("id", str(conversation_id))
            .execute()
        )
        if result.data:
            return Conversation(**result.data[0])
        return None

    async def update_conversation_summary(
        self,
        conversation_id: UUID,
        summary: str,
    ) -> Optional[Conversation]:
        """Update conversation rolling summary."""
        result = (
            self.client.table("conversations")
            .update({"summary": summary})
            .eq("id", str(conversation_id))
            .execute()
        )
        if result.data:
            return Conversation(**result.data[0])
        return None

    async def get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 50,
    ) -> List[Message]:
        """Get recent messages for a conversation."""
        result = (
            self.client.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        messages = [Message(**msg) for msg in result.data]
        return list(reversed(messages))  # Return in chronological order

    # Message operations
    async def save_message(self, message: MessageCreate) -> Message:
        """Save a message to the conversation."""
        data = message.model_dump()
        result = self.client.table("messages").insert(data).execute()
        return Message(**result.data[0])

    async def save_messages(self, messages: List[MessageCreate]) -> List[Message]:
        """Bulk save messages."""
        data = [msg.model_dump() for msg in messages]
        result = self.client.table("messages").insert(data).execute()
        return [Message(**msg) for msg in result.data]

    # Ticket operations
    async def create_ticket(self, ticket: TicketCreate) -> Ticket:
        """Create a support ticket."""
        data = ticket.model_dump()
        result = self.client.table("tickets").insert(data).execute()
        return Ticket(**result.data[0])

    async def get_tickets(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Ticket]:
        """Get tickets with optional status filter."""
        query = self.client.table("tickets").select("*").order("created_at", desc=True).limit(limit)
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return [Ticket(**ticket) for ticket in result.data]

    async def get_ticket_by_id(self, ticket_id: UUID) -> Optional[Ticket]:
        """Get a specific ticket by ID."""
        result = self.client.table("tickets").select("*").eq("id", str(ticket_id)).execute()
        if result.data:
            return Ticket(**result.data[0])
        return None

    async def update_ticket_status(
        self,
        ticket_id: UUID,
        status: str,
    ) -> Optional[Ticket]:
        """Update ticket status."""
        result = (
            self.client.table("tickets")
            .update({"status": status})
            .eq("id", str(ticket_id))
            .execute()
        )
        if result.data:
            return Ticket(**result.data[0])
        return None

    # Handoff operations
    async def create_handoff(self, handoff: HandoffCreate) -> Handoff:
        """Create a handoff/escalation record."""
        data = handoff.model_dump()
        result = self.client.table("handoffs").insert(data).execute()
        return Handoff(**result.data[0])

    async def get_handoffs(
        self,
        limit: int = 100,
    ) -> List[Handoff]:
        """Get recent handoffs."""
        result = (
            self.client.table("handoffs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [Handoff(**h) for h in result.data]

    async def get_handoff_by_conversation(self, conversation_id: UUID) -> Optional[Handoff]:
        """Get handoff for a specific conversation."""
        result = (
            self.client.table("handoffs")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return Handoff(**result.data[0])
        return None

    # Realtime subscription helpers (for admin dashboard)
    def subscribe_to_tickets(self, callback):
        """Subscribe to realtime ticket changes."""
        return (
            self.client.table("tickets")
            .on("*", callback)
            .subscribe()
        )

    def subscribe_to_handoffs(self, callback):
        """Subscribe to realtime handoff changes."""
        return (
            self.client.table("handoffs")
            .on("*", callback)
            .subscribe()
        )

    def subscribe_to_conversations(self, callback):
        """Subscribe to realtime conversation changes."""
        return (
            self.client.table("conversations")
            .on("*", callback)
            .subscribe()
        )


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create the singleton Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client