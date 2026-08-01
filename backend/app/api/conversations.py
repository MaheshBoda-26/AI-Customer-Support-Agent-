"""
Conversations API endpoints.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query

from app.db.supabase_client import get_supabase_client
from app.db.models import Conversation, Message

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = get_supabase_client()


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: UUID):
    """Get a conversation by ID."""
    conversation = await supabase.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=list[Message])
async def get_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(default=50, le=200),
):
    """Get messages for a conversation."""
    # Verify conversation exists
    conversation = await supabase.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await supabase.get_conversation_history(conversation_id, limit=limit)
    return messages