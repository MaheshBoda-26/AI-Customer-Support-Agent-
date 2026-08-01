"""
LangGraph agent state schema.
"""
from typing import List, Optional, TypedDict
from uuid import UUID
from dataclasses import dataclass


class AgentState(TypedDict):
    """State passed through the LangGraph agent."""
    # Conversation identifiers
    conversation_id: str
    customer_id: Optional[str]

    # Input
    user_input: str
    detected_language: str

    # Retrieved context
    retrieved_docs: List[str]

    # Classification
    intent: Optional[str]          # question | complaint | refund_request | bug | account | other
    confidence: float

    # Routing decisions
    ticket_needed: bool
    escalate: bool
    handoff_reason: Optional[str]

    # Output
    response: str

    # Metadata
    retrieval_failed: bool
    token_usage: dict


@dataclass
class AgentConfig:
    """Configuration for the agent."""
    confidence_threshold: float = 0.7
    max_retry_attempts: int = 2
    default_top_k: int = 5