"""
Unit tests for Supabase database operations.

These tests use mocking to avoid requiring a real Supabase connection.
Run with: pytest backend/tests/test_db.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.db.supabase_client import SupabaseClient
from app.db.models import (
    Customer, CustomerCreate,
    Conversation, ConversationCreate,
    Message, MessageCreate,
    Ticket, TicketCreate,
    Handoff, HandoffCreate,
    ConversationStatus,
    TicketStatus, TicketPriority, TicketCategory,
)


@pytest.fixture
def mock_supabase_client():
    """Create a SupabaseClient with mocked underlying client."""
    with patch('app.db.supabase_client.create_client') as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        client = SupabaseClient()
        client.client = mock_client
        yield client, mock_client


@pytest.fixture
def sample_customer():
    return Customer(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_conversation():
    return Conversation(
        id=uuid4(),
        customer_id=uuid4(),
        status=ConversationStatus.ACTIVE,
        language="en",
        summary=None,
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_message():
    return Message(
        id=uuid4(),
        conversation_id=uuid4(),
        role="user",
        content="Hello, I need help!",
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_ticket():
    return Ticket(
        id=uuid4(),
        conversation_id=uuid4(),
        subject="Test Ticket",
        description="Test description",
        category=TicketCategory.OTHER,
        status=TicketStatus.OPEN,
        priority=TicketPriority.NORMAL,
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_handoff():
    return Handoff(
        id=uuid4(),
        conversation_id=uuid4(),
        reason="Customer requested human",
        assigned_to=None,
        created_at=datetime.now(),
    )


class TestCustomerOperations:
    """Tests for customer-related operations."""

    async def test_get_or_create_customer_existing(self, mock_supabase_client, sample_customer):
        client, mock = mock_supabase_client
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            sample_customer.model_dump()
        ]

        result = await client.get_or_create_customer("test@example.com", "Test User")

        assert result.email == "test@example.com"
        assert result.name == "Test User"

    async def test_get_or_create_customer_new(self, mock_supabase_client, sample_customer):
        client, mock = mock_supabase_client
        # First call returns empty (no existing customer)
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        # Second call (insert) returns the new customer
        mock.table.return_value.insert.return_value.execute.return_value.data = [
            sample_customer.model_dump()
        ]

        result = await client.get_or_create_customer("new@example.com", "New User")

        assert result.email == "new@example.com"
        mock.table.return_value.insert.assert_called_once()


class TestConversationOperations:
    """Tests for conversation-related operations."""

    async def test_create_conversation(self, mock_supabase_client, sample_conversation):
        client, mock = mock_supabase_client
        mock.table.return_value.insert.return_value.execute.return_value.data = [
            sample_conversation.model_dump()
        ]

        conv_create = ConversationCreate(
            customer_id=sample_conversation.customer_id,
            status=ConversationStatus.ACTIVE,
            language="en",
        )
        result = await client.create_conversation(conv_create)

        assert result.id == sample_conversation.id
        mock.table.return_value.insert.assert_called_once()

    async def test_get_conversation_found(self, mock_supabase_client, sample_conversation):
        client, mock = mock_supabase_client
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            sample_conversation.model_dump()
        ]

        result = await client.get_conversation(sample_conversation.id)

        assert result is not None
        assert result.id == sample_conversation.id

    async def test_get_conversation_not_found(self, mock_supabase_client):
        client, mock = mock_supabase_client
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        result = await client.get_conversation(uuid4())

        assert result is None

    async def test_update_conversation_status(self, mock_supabase_client, sample_conversation):
        client, mock = mock_supabase_client
        updated_conv = sample_conversation.model_copy(update={"status": ConversationStatus.ESCALATED})
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            updated_conv.model_dump()
        ]

        result = await client.update_conversation_status(
            sample_conversation.id,
            ConversationStatus.ESCALATED
        )

        assert result is not None
        assert result.status == ConversationStatus.ESCALATED

    async def test_update_conversation_summary(self, mock_supabase_client, sample_conversation):
        client, mock = mock_supabase_client
        updated_conv = sample_conversation.model_copy(update={"summary": "Customer needs billing help"})
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            updated_conv.model_dump()
        ]

        result = await client.update_conversation_summary(
            sample_conversation.id,
            "Customer needs billing help"
        )

        assert result is not None
        assert result.summary == "Customer needs billing help"

    async def test_get_conversation_history(self, mock_supabase_client, sample_message):
        client, mock = mock_supabase_client
        messages = [
            sample_message.model_dump(),
            sample_message.model_copy(update={"role": "assistant", "content": "How can I help?"}).model_dump(),
        ]
        mock.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = messages

        result = await client.get_conversation_history(sample_message.conversation_id, limit=10)

        assert len(result) == 2
        assert result[0].role == "user"
        assert result[1].role == "assistant"


class TestMessageOperations:
    """Tests for message-related operations."""

    async def test_save_message(self, mock_supabase_client, sample_message):
        client, mock = mock_supabase_client
        mock.table.return_value.insert.return_value.execute.return_value.data = [
            sample_message.model_dump()
        ]

        msg_create = MessageCreate(
            conversation_id=sample_message.conversation_id,
            role="user",
            content="Test message",
        )
        result = await client.save_message(msg_create)

        assert result.content == "Test message"
        mock.table.return_value.insert.assert_called_once()

    async def test_save_messages_bulk(self, mock_supabase_client, sample_message):
        client, mock = mock_supabase_client
        messages = [
            sample_message.model_dump(),
            sample_message.model_copy(update={"role": "assistant", "content": "Response"}).model_dump(),
        ]
        mock.table.return_value.insert.return_value.execute.return_value.data = messages

        msg_creates = [
            MessageCreate(conversation_id=sample_message.conversation_id, role="user", content="Test"),
            MessageCreate(conversation_id=sample_message.conversation_id, role="assistant", content="Response"),
        ]
        result = await client.save_messages(msg_creates)

        assert len(result) == 2


class TestTicketOperations:
    """Tests for ticket-related operations."""

    async def test_create_ticket(self, mock_supabase_client, sample_ticket):
        client, mock = mock_supabase_client
        mock.table.return_value.insert.return_value.execute.return_value.data = [
            sample_ticket.model_dump()
        ]

        ticket_create = TicketCreate(
            conversation_id=sample_ticket.conversation_id,
            subject="Test Ticket",
            description="Test description",
            category=TicketCategory.BUG,
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
        )
        result = await client.create_ticket(ticket_create)

        assert result.subject == "Test Ticket"
        assert result.category == TicketCategory.BUG

    async def test_get_tickets_with_status_filter(self, mock_supabase_client, sample_ticket):
        client, mock = mock_supabase_client
        mock.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            sample_ticket.model_dump()
        ]

        # Test with status filter
        mock.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            sample_ticket.model_dump()
        ]

        result = await client.get_tickets(status="open", limit=50)

        assert len(result) == 1

    async def test_get_tickets_no_filter(self, mock_supabase_client, sample_ticket):
        client, mock = mock_supabase_client
        mock.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            sample_ticket.model_dump()
        ]

        result = await client.get_tickets(limit=50)

        assert len(result) == 1

    async def test_get_ticket_by_id(self, mock_supabase_client, sample_ticket):
        client, mock = mock_supabase_client
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            sample_ticket.model_dump()
        ]

        result = await client.get_ticket_by_id(sample_ticket.id)

        assert result is not None
        assert result.id == sample_ticket.id

    async def test_update_ticket_status(self, mock_supabase_client, sample_ticket):
        client, mock = mock_supabase_client
        updated_ticket = sample_ticket.model_copy(update={"status": TicketStatus.IN_PROGRESS})
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            updated_ticket.model_dump()
        ]

        result = await client.update_ticket_status(sample_ticket.id, TicketStatus.IN_PROGRESS.value)

        assert result is not None
        assert result.status == TicketStatus.IN_PROGRESS


class TestHandoffOperations:
    """Tests for handoff-related operations."""

    async def test_create_handoff(self, mock_supabase_client, sample_handoff):
        client, mock = mock_supabase_client
        mock.table.return_value.insert.return_value.execute.return_value.data = [
            sample_handoff.model_dump()
        ]

        handoff_create = HandoffCreate(
            conversation_id=sample_handoff.conversation_id,
            reason="Customer requested human agent",
            assigned_to=None,
        )
        result = await client.create_handoff(handoff_create)

        assert result.reason == "Customer requested human agent"

    async def test_get_handoffs(self, mock_supabase_client, sample_handoff):
        client, mock = mock_supabase_client
        mock.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            sample_handoff.model_dump()
        ]

        result = await client.get_handoffs(limit=50)

        assert len(result) == 1

    async def test_get_handoff_by_conversation(self, mock_supabase_client, sample_handoff):
        client, mock = mock_supabase_client
        mock.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            sample_handoff.model_dump()
        ]

        result = await client.get_handoff_by_conversation(sample_handoff.conversation_id)

        assert result is not None
        assert result.conversation_id == sample_handoff.conversation_id


class TestRealtimeSubscriptions:
    """Tests for realtime subscription helpers."""

    def test_subscribe_to_tickets(self, mock_supabase_client):
        client, mock = mock_supabase_client
        mock_callback = MagicMock()
        mock_channel = MagicMock()
        mock.table.return_value.on.return_value.subscribe.return_value = mock_channel

        result = client.subscribe_to_tickets(mock_callback)

        mock.table.assert_called_with("tickets")
        mock.table.return_value.on.assert_called_with("*", mock_callback)
        assert result == mock_channel

    def test_subscribe_to_handoffs(self, mock_supabase_client):
        client, mock = mock_supabase_client
        mock_callback = MagicMock()
        mock_channel = MagicMock()
        mock.table.return_value.on.return_value.subscribe.return_value = mock_channel

        result = client.subscribe_to_handoffs(mock_callback)

        mock.table.assert_called_with("handoffs")

    def test_subscribe_to_conversations(self, mock_supabase_client):
        client, mock = mock_supabase_client
        mock_callback = MagicMock()
        mock_channel = MagicMock()
        mock.table.return_value.on.return_value.subscribe.return_value = mock_channel

        result = client.subscribe_to_conversations(mock_callback)

        mock.table.assert_called_with("conversations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])