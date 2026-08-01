"""
LangGraph agent graph definition and compilation.
"""
from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes import (
    classify_intent,
    retrieve_context,
    generate_response,
    route_decision,
    create_ticket_node,
    handoff_node,
    persist_node,
)


def should_create_ticket(state: AgentState) -> str:
    """Conditional edge: route to ticket creation if needed."""
    return "create_ticket" if state.get("ticket_needed", False) else "handoff_check"


def should_escalate(state: AgentState) -> str:
    """Conditional edge: route to handoff if needed."""
    return "handoff" if state.get("escalate", False) else "persist"


def create_agent_graph():
    """Create and compile the LangGraph agent."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("route_decision", route_decision)
    workflow.add_node("create_ticket", create_ticket_node)
    workflow.add_node("handoff", handoff_node)
    workflow.add_node("persist", persist_node)

    # Define edges
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "retrieve_context")
    workflow.add_edge("retrieve_context", "generate_response")
    workflow.add_edge("generate_response", "route_decision")

    # Conditional routing after route_decision
    workflow.add_conditional_edges(
        "route_decision",
        should_create_ticket,
        {
            "create_ticket": "create_ticket",
            "handoff_check": "handoff",
        }
    )

    workflow.add_conditional_edges(
        "create_ticket",
        should_escalate,
        {
            "handoff": "handoff",
            "persist": "persist",
        }
    )

    workflow.add_conditional_edges(
        "handoff",
        lambda _: "persist",
        {"persist": "persist"}
    )

    workflow.add_edge("persist", END)

    return workflow.compile()


# Compiled graph instance
agent_graph = create_agent_graph()