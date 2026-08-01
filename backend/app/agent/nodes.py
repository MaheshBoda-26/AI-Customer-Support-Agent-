"""
LangGraph agent node functions.
"""
import json
import logging
from typing import List, Optional
from uuid import uuid4

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.agent.state import AgentState, AgentConfig
from app.agent.prompts import (
    SYSTEM_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
    ROUTE_DECISION_PROMPT,
    LANGUAGE_DETECTION_PROMPT,
    format_system_prompt,
)
from app.rag.retriever import get_retriever, RetrievedChunk
from app.db.supabase_client import get_supabase_client
from app.db.models import MessageCreate, MessageRole, TicketCreate, HandoffCreate, TicketCategory, TicketPriority

logger = logging.getLogger(__name__)

# Initialize NVIDIA NIM client
nvidia_nim_client = OpenAI(
    api_key=settings.NVIDIA_NIM_API_KEY,
    base_url=settings.NVIDIA_NIM_BASE_URL,
)
retriever = get_retriever()
supabase = get_supabase_client()
agent_config = AgentConfig(confidence_threshold=settings.CONFIDENCE_THRESHOLD)


def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent and detect language."""
    logger.info(f"Classifying intent for conversation {state['conversation_id']}")

    prompt = f"{INTENT_CLASSIFICATION_PROMPT}\n\nUser message: {state['user_input']}"

    try:
        response = _call_nvidia_nim(prompt, model=settings.NVIDIA_NIM_FAST_MODEL, max_tokens=200)
        result = json.loads(response.strip())

        state["intent"] = result.get("intent", "question")
        state["confidence"] = float(result.get("confidence", 0.5))
        state["detected_language"] = result.get("language", "en")

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        # Fallback
        state["intent"] = "question"
        state["confidence"] = 0.5
        state["detected_language"] = "en"

    logger.info(f"Intent: {state['intent']}, Confidence: {state['confidence']}, Language: {state['detected_language']}")
    return state


def retrieve_context(state: AgentState) -> AgentState:
    """Retrieve relevant knowledge base chunks."""
    logger.info(f"Retrieving context for conversation {state['conversation_id']}")

    try:
        # Use detected language, but default to "en" if not set or invalid
        lang = state.get("detected_language", "en")
        if lang not in ["en", "es", "fr", "de", "ja", "zh", "ko", "pt", "it", "ru"]:
            lang = "en"

        chunks: List[RetrievedChunk] = retriever.retrieve(
            query=state["user_input"],
            top_k=agent_config.default_top_k,
            language=lang,
        )
        state["retrieved_docs"] = [chunk.text for chunk in chunks]
        state["retrieval_failed"] = False
        logger.info(f"Retrieved chunks: {[c.text[:50] for c in chunks]}")
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        state["retrieved_docs"] = []
        state["retrieval_failed"] = True
        # Lower confidence when retrieval fails
        state["confidence"] = min(state["confidence"], 0.5)

    logger.info(f"Retrieved {len(state['retrieved_docs'])} chunks")
    return state


def generate_response(state: AgentState) -> AgentState:
    """Generate response using NVIDIA NIM with retrieved context."""
    logger.info(f"Generating response for conversation {state['conversation_id']}")

    # Build conversation history
    history_messages = []
    for msg in state.get("messages", []):
        role = "Human" if msg.get("role") == "user" else "Assistant"
        history_messages.append(f"{role}: {msg.get('content', '')}")

    conversation_history = "\n".join(history_messages[-10:])  # Last 10 messages

    # Format prompt
    prompt = format_system_prompt(
        retrieved_docs=state["retrieved_docs"],
        conversation_history=conversation_history,
        user_input=state["user_input"],
    )

    try:
        response = _call_nvidia_nim(prompt, model=settings.NVIDIA_NIM_MODEL, max_tokens=1000)
        state["response"] = response.strip()
        state["token_usage"] = {"model": settings.NVIDIA_NIM_MODEL}
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        state["response"] = "I'm sorry, I'm having trouble generating a response right now. Please try again."
        state["confidence"] = 0.0

    return state


def route_decision(state: AgentState) -> AgentState:
    """Decide if ticket creation or escalation is needed."""
    logger.info(f"Making routing decision for conversation {state['conversation_id']}")

    # Build context for routing decision
    context = f"""
Conversation ID: {state['conversation_id']}
Intent: {state['intent']}
Confidence: {state['confidence']}
Language: {state['detected_language']}
User Message: {state['user_input']}
Retrieved Docs Count: {len(state['retrieved_docs'])}
Retrieval Failed: {state['retrieval_failed']}
"""

    prompt = f"{ROUTE_DECISION_PROMPT}\n\nContext:\n{context}"

    try:
        response = _call_nvidia_nim(prompt, model=settings.NVIDIA_NIM_FAST_MODEL, max_tokens=300)
        result = json.loads(response.strip())

        state["ticket_needed"] = result.get("ticket_needed", False)
        state["escalate"] = result.get("escalate", False)
        state["handoff_reason"] = result.get("handoff_reason")

        # Auto-escalate on low confidence
        if state["confidence"] < agent_config.confidence_threshold:
            state["escalate"] = True
            state["handoff_reason"] = state["handoff_reason"] or f"Low confidence ({state['confidence']:.2f})"

        # Auto-escalate on sensitive topics
        sensitive_intents = ["account", "refund_request"]
        if state["intent"] in sensitive_intents and state["confidence"] < 0.8:
            state["escalate"] = True
            state["handoff_reason"] = state["handoff_reason"] or f"Sensitive topic: {state['intent']}"

    except Exception as e:
        logger.error(f"Route decision failed: {e}")
        # Safe default: escalate on error
        state["ticket_needed"] = True
        state["escalate"] = True
        state["handoff_reason"] = f"Routing error: {str(e)}"

    logger.info(f"Routing: ticket_needed={state['ticket_needed']}, escalate={state['escalate']}")
    return state


async def create_ticket_node(state: AgentState) -> AgentState:
    """Create a support ticket in Supabase."""
    if not state["ticket_needed"]:
        return state

    logger.info(f"Creating ticket for conversation {state['conversation_id']}")

    try:
        # Determine category and priority from intent
        category_map = {
            "refund_request": TicketCategory.BILLING,
            "bug": TicketCategory.BUG,
            "account": TicketCategory.ACCOUNT,
        }
        priority_map = {
            "refund_request": TicketPriority.HIGH,
            "bug": TicketPriority.NORMAL,
            "account": TicketPriority.HIGH,
        }

        ticket = TicketCreate(
            conversation_id=uuid4() if not state["conversation_id"] else state["conversation_id"],
            subject=f"Support Request: {state['intent'].replace('_', ' ').title()}",
            description=f"Customer message: {state['user_input']}\n\nAgent response: {state['response']}",
            category=category_map.get(state["intent"], TicketCategory.OTHER),
            priority=priority_map.get(state["intent"], TicketPriority.NORMAL),
        )

        created_ticket = await supabase.create_ticket(ticket)
        state["ticket_id"] = str(created_ticket.id)
        logger.info(f"Created ticket {created_ticket.id}")

    except Exception as e:
        logger.error(f"Ticket creation failed: {e}")
        # Don't block the response on ticket creation failure

    return state


async def handoff_node(state: AgentState) -> AgentState:
    """Create handoff record and update conversation status."""
    if not state["escalate"]:
        return state

    logger.info(f"Creating handoff for conversation {state['conversation_id']}")

    try:
        handoff = HandoffCreate(
            conversation_id=state["conversation_id"],
            reason=state["handoff_reason"] or "Escalated by agent",
            assigned_to=None,  # Would be assigned to specific agent
        )
        await supabase.create_handoff(handoff)
        await supabase.update_conversation_status(
            state["conversation_id"],
            "escalated"
        )
        logger.info("Handoff created and conversation marked as escalated")

        # TODO: Send Slack notification if webhook configured

    except Exception as e:
        logger.error(f"Handoff creation failed: {e}")

    return state


async def persist_node(state: AgentState) -> AgentState:
    """Persist messages to Supabase."""
    logger.info(f"Persisting messages for conversation {state['conversation_id']}")

    try:
        messages = [
            MessageCreate(
                conversation_id=state["conversation_id"],
                role=MessageRole.USER,
                content=state["user_input"],
            ),
            MessageCreate(
                conversation_id=state["conversation_id"],
                role=MessageRole.ASSISTANT,
                content=state["response"],
            ),
        ]
        await supabase.save_messages(messages)
        logger.info("Messages persisted successfully")
    except Exception as e:
        logger.error(f"Message persistence failed: {e}")
        # Critical: log for manual recovery but don't fail the response

    return state


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True
)
def _call_nvidia_nim(prompt: str, model: str, max_tokens: int) -> str:
    """Call NVIDIA NIM API with retry logic."""
    response = nvidia_nim_client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content