# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AI Customer Support Agent** - a 24×7 support executive that answers customer questions using company documentation (RAG), conversation history, and internal knowledge. It escalates to humans when needed and creates support tickets automatically.

**Tech Stack:**
- **LLM:** OpenRouter (Claude models) - Sonnet for generation, Haiku for classification
- **Agent Orchestration:** LangGraph
- **Vector DB:** Qdrant (KB chunks, voyage-3 embeddings)
- **Relational DB / Auth / Realtime:** Supabase (Postgres)
- **Backend:** FastAPI
- **Frontend:** Next.js 14+ (App Router) with Tailwind CSS
- **Hosting:** Backend on Fly.io/Railway/Render, Frontend on Vercel, Qdrant Cloud

## Repository Structure

```
support-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint
│   │   ├── api/                       # Route handlers (chat, tickets, ingest)
│   │   ├── agent/                     # LangGraph agent core
│   │   │   ├── graph.py               # Graph definition & compilation
│   │   │   ├── nodes.py               # Node functions (classify, retrieve, generate, route)
│   │   │   ├── state.py               # AgentState TypedDict schema
│   │   │   └── prompts.py             # System prompts
│   │   ├── rag/                       # RAG utilities
│   │   │   ├── embed.py               # Embedding client wrapper
│   │   │   ├── retriever.py           # Qdrant query logic
│   │   │   └── chunker.py             # Text chunking logic
│   │   ├── db/                        # Data layer
│   │   │   ├── supabase_client.py     # Supabase client + query wrappers
│   │   │   └── models.py              # Pydantic models mirroring DB schema
│   │   └── core/                      # Cross-cutting concerns
│   │       ├── config.py              # Env var loading, settings
│   │       └── logging.py             # Structured logging
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── (widget)/chat/page.tsx     # Chat widget page
│   │   └── (admin)/dashboard/page.tsx # Admin dashboard page
│   ├── components/
│   │   ├── ChatWindow.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── TicketList.tsx
│   │   └── HandoffQueue.tsx
│   ├── lib/
│   │   ├── api.ts                     # Fetch wrappers for backend calls
│   │   └── supabaseClient.ts          # Supabase client (realtime)
│   ├── package.json
│   └── tailwind.config.ts
├── ingestion/
│   └── ingest_docs.py                 # Standalone KB ingestion script
└── docker-compose.yml                 # Local dev: Qdrant + backend + frontend
```

## Key Documentation Files

- **Architecture.md** - System architecture, folder structure, component responsibilities
- **PRD.md** - Product requirements, user stories, acceptance criteria
- **Design.md** - Design system (colors, typography, CSS variables, component styles)
- **Implementation Plan.md** - Detailed technical implementation plan
- **Phases.md** - 10-phase step-by-step build guide (currently in Phase 0)
- **Rules.md** - Working rules: what to use/avoid, libraries, error handling, agent boundaries
- **TRD.md** - Technical requirements, data models, API specs, agent state schema

## Development Commands

### Backend (Python/FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# Or with Docker:
docker-compose up backend
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
# Or with Docker:
docker-compose up frontend
```

### Ingestion Script
```bash
cd ingestion
python ingest_docs.py
```

### Testing
```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests (when added)
cd frontend
npm test
```

## Important Rules (from Rules.md)

### What We Use
- Python 3.11+, FastAPI, LangGraph, Pydantic, OpenAI SDK (for OpenRouter), Qdrant, Supabase
- Next.js (App Router), React, TypeScript, Tailwind CSS, Supabase JS client, Zod
- Docker for local dev and deployment

### What We Avoid
- No mixing vector stores (Qdrant only)
- No mixing relational stores (Supabase only)
- No business logic in route handlers - keep in `agent/` or `db/`
- All prompts in `agent/prompts.py` only
- No silent failures - retry with tenacity, log everything
- No client-side secrets
- No unbounded conversation history - use sliding window + summary
- No answers without retrieval grounding (except greetings)
- No `any` types in TypeScript

### Error Handling
- OpenRouter API: retry with exponential backoff (max 3), then graceful fallback
- Qdrant: retry once, proceed without context but flag `retrieval_failed=True`
- Supabase: retry once, log full context for manual recovery
- Malformed LLM output: retry once with stricter prompt, then escalate
- Unhandled exceptions: catch at `/chat` handler, generic message to customer, full trace logged

### Agent Boundaries
- MUST: Ground answers in KB, escalate on low confidence/explicit request/sensitive topics, preserve context, respect language
- MUST NOT: Invent policies, make binding decisions, pretend to be human, loop indefinitely, access/modify account data beyond scope, store sensitive data

## Agent State Schema (LangGraph)

```python
class AgentState(TypedDict):
    conversation_id: str
    messages: List[dict]
    user_input: str
    detected_language: str
    retrieved_docs: List[str]
    intent: Optional[str]        # question | complaint | refund_request | bug | other
    confidence: float
    ticket_needed: bool
    escalate: bool
    response: str
```

Nodes: `classify_intent` → `retrieve_context` → `generate_response` → `route_decision` → (`create_ticket_node` | `handoff_node`) → `persist_node`

## API Endpoints

- `POST /chat` - Main chat endpoint, invokes LangGraph agent
- `GET /conversations/{id}` - Get conversation history
- `GET/PATCH /tickets` - Ticket management
- `POST /ingest` - KB ingestion endpoint

## Environment Variables (backend/.env)

```
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_FAST_MODEL=anthropic/claude-3-haiku
QDRANT_URL=
QDRANT_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
EMBEDDING_MODEL=voyage-3
```

## Current Phase

**Phase 0: Project Setup** - Setting up accounts, keys, repo skeleton. See Phases.md for detailed steps.

## Design System

See Design.md for complete design tokens. Key colors:
- Primary: `#E8722C` (orange)
- Accent: `#F2A65A`
- Light/Dark mode CSS variables defined in Design.md Section 3
- Typography: Roboto font family
- Border radius: 8px (buttons/inputs), 12px (cards/bubbles)

## Testing & Evaluation Targets (from PRD)

- Deflection rate: ≥ 60% within 3 months
- Answer accuracy: ≥ 90%
- Hallucination rate: < 2%
- First-response time: < 3 seconds
- Ticket auto-creation accuracy: ≥ 95%
- CSAT on AI-only chats: ≥ 4/5

## References

For detailed implementation guidance, always check:
1. Rules.md - for code standards and boundaries
2. Architecture.md - for system structure
3. Phases.md - for current build phase steps
4. TRD.md - for technical specs and data models