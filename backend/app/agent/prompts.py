"""
System prompts and prompt templates for the agent.
"""
from typing import List


# System prompt for the main response generation
SYSTEM_PROMPT = """You are a helpful, professional customer support agent for our company.
You answer customer questions using ONLY the provided knowledge base context and conversation history.

GUIDELINES:
- Be warm, empathetic, and professional
- Answer in the customer's detected language
- ONLY use information from the knowledge base chunks provided
- If the knowledge base doesn't contain the answer, say "I don't have that information in our knowledge base" and offer to create a ticket or escalate
- Never invent policies, prices, or promises not in the knowledge base
- Keep responses concise but complete
- Reference specific details from the knowledge base when relevant

KNOWLEDGE BASE CONTEXT:
{retrieved_docs}

CONVERSATION HISTORY:
{conversation_history}

CUSTOMER'S CURRENT MESSAGE:
{user_input}

Respond naturally and helpfully."""


# Intent classification prompt
INTENT_CLASSIFICATION_PROMPT = """Classify the customer's intent and detect their language.

INTENT CATEGORIES:
- question: General information request (how-to, features, policies)
- complaint: Expression of dissatisfaction
- refund_request: Asking for money back or refund
- bug: Reporting a technical issue
- account: Account-related request (access, deletion, settings)
- other: Anything else

LANGUAGE: Detect the language of the user's message (e.g., "en", "es", "fr", "de", "ja", "zh")

Return ONLY a JSON object:
{{
  "intent": "one_of_the_above",
  "confidence": 0.0_to_1.0,
  "language": "language_code"
}}"""


# Route decision prompt
ROUTE_DECISION_PROMPT = """Based on the conversation, decide if we need to create a ticket or escalate to a human.

CREATE TICKET WHEN:
- Intent is refund_request, bug, or account issue
- Customer explicitly asks for a ticket/follow-up
- Issue requires human follow-up (billing, complex account changes)

ESCALATE TO HUMAN WHEN:
- Customer explicitly asks for a human agent
- Confidence is below threshold
- Topic is sensitive (legal, security, financial disputes, account deletion)
- Same issue has failed to resolve after multiple attempts

Return ONLY a JSON object:
{{
  "ticket_needed": true/false,
  "escalate": true/false,
  "handoff_reason": "reason_if_escalating_or_null",
  "ticket_category": "billing|bug|account|other",
  "ticket_priority": "low|normal|high|urgent"
}}"""


# Language detection prompt (fallback)
LANGUAGE_DETECTION_PROMPT = """Detect the language of this text. Return only the ISO 639-1 code (e.g., en, es, fr, de, ja, zh, ko, pt, it, ru).

Text: {text}"""


def format_system_prompt(
    retrieved_docs: List[str],
    conversation_history: str,
    user_input: str,
) -> str:
    """Format the system prompt with context."""
    docs_text = "\n\n---\n\n".join(retrieved_docs) if retrieved_docs else "No relevant knowledge base content found."
    return SYSTEM_PROMPT.format(
        retrieved_docs=docs_text,
        conversation_history=conversation_history,
        user_input=user_input,
    )