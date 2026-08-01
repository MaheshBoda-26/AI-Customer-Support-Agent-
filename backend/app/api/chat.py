"""
Chat API endpoint - main entrypoint for customer messages.
"""
import logging
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.agent.graph import agent_graph
from app.agent.state import AgentState
from app.db.supabase_client import get_supabase_client
from app.db.models import ChatRequest, ChatResponse, ConversationCreate, ConversationStatus

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = get_supabase_client()


class ChatRequestExtended(ChatRequest):
    """Extended chat request with optional customer info."""
    pass


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequestExtended,
    background_tasks: BackgroundTasks,
):
    """
    Process a customer message through the agent graph.
    Returns the agent's response along with ticket/escalation status.
    """
    logger.info(f"Chat request received: conversation_id={request.conversation_id}")

    try:
        # Get or create conversation
        conversation_id = request.conversation_id or uuid4()
        customer_id = None

        if request.customer_email:
            customer = await supabase.get_or_create_customer(
                email=request.customer_email,
                name=request.customer_name,
            )
            customer_id = str(customer.id)

        # Get existing conversation or create new
        conversation = await supabase.get_conversation(conversation_id)
        if not conversation:
            conversation = await supabase.create_conversation(
                ConversationCreate(
                    customer_id=customer_id,
                    status=ConversationStatus.ACTIVE,
                )
            )
            conversation_id = conversation.id

        # Get conversation history
        history = await supabase.get_conversation_history(conversation_id, limit=20)
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]

        # Build agent state
        initial_state: AgentState = {
            "conversation_id": str(conversation_id),
            "customer_id": customer_id,
            "messages": messages,
            "user_input": request.message,
            "detected_language": "en",  # Will be updated by classify_intent
            "retrieved_docs": [],
            "intent": None,
            "confidence": 1.0,
            "ticket_needed": False,
            "escalate": False,
            "handoff_reason": None,
            "response": "",
            "retrieval_failed": False,
            "token_usage": {},
        }

        # Invoke the agent graph
        final_state = await agent_graph.ainvoke(initial_state)

        # Build response
        response = ChatResponse(
            response=final_state["response"],
            conversation_id=conversation_id,
            ticket_created=final_state.get("ticket_needed", False),
            escalated=final_state.get("escalate", False),
            ticket_id=final_state.get("ticket_id"),
        )

        logger.info(f"Chat response generated: ticket_created={response.ticket_created}, escalated={response.escalated}")
        return response

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")