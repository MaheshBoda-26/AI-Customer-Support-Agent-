"""
Pydantic models mirroring the Supabase database schema.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    CLOSED = "closed"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class TicketPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    ACCOUNT = "account"
    OTHER = "other"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class CustomerBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class Customer(CustomerBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    customer_id: Optional[UUID] = None
    status: ConversationStatus = ConversationStatus.ACTIVE
    language: str = "en"


class ConversationCreate(ConversationBase):
    pass


class Conversation(ConversationBase):
    id: UUID
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    conversation_id: UUID
    role: MessageRole
    content: str


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class TicketBase(BaseModel):
    conversation_id: UUID
    subject: str
    description: str
    category: TicketCategory = TicketCategory.OTHER
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.NORMAL


class TicketCreate(TicketBase):
    pass


class Ticket(TicketBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class HandoffBase(BaseModel):
    conversation_id: UUID
    reason: str
    assigned_to: Optional[str] = None


class HandoffCreate(HandoffBase):
    pass


class Handoff(HandoffBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# API Request/Response models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[UUID] = None
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: UUID
    ticket_created: bool = False
    escalated: bool = False
    ticket_id: Optional[UUID] = None


class IngestRequest(BaseModel):
    source: str = Field(..., description="Document source identifier")
    content: str = Field(..., min_length=1, description="Document content")
    title: Optional[str] = None
    section: Optional[str] = None
    language: str = "en"