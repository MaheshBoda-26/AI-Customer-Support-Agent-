# Architecture Document
## AI Customer Support Agent

**Version:** 1.0
**Last updated:** July 27, 2026

---

## 1. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| LLM | OpenRouter (Claude models) | Reasoning, intent classification, response generation |
| Agent orchestration | LangGraph | Graph-based control flow for the agent |
| Vector DB | Qdrant | Stores embedded KB chunks for RAG retrieval |
| Relational DB / Auth / Realtime | Supabase (Postgres) | Conversations, messages, tickets, handoffs, customers |
| Backend framework | FastAPI | REST API layer, agent invocation |
| Frontend framework | Next.js | Chat widget + admin dashboard |
| Embeddings | Voyage AI (`voyage-3`) or OpenAI | Turns text into vectors for search |
| Hosting — backend | Fly.io / Railway / Render | Containerized FastAPI |
| Hosting — frontend | Vercel | Next.js deployment |
| Hosting — vector DB | Qdrant Cloud | Managed Qdrant instance |

---

## 2. App Flow

### 2.1 Customer-facing flow

1. Customer opens the chat widget on the website/app.
2. Customer types a message and hits send.
3. Widget calls `POST /chat` with the message and `conversation_id` (or none, for a new session).
4. Backend loads prior message history from Supabase.
5. LangGraph agent runs:
   - Detects intent and language.
   - Embeds the query, searches Qdrant for relevant KB chunks.
   - Generates a response with Claude, grounded in retrieved chunks + conversation history.
   - Decides whether to create a ticket and/or escalate to a human.
6. Response streams back to the widget; ticket/escalation status returned alongside.
7. Messages, tickets, and handoffs are persisted to Supabase.
8. If escalated, conversation status flips to `escalated` and a human agent is notified.

### 2.2 Human agent flow

1. Agent dashboard subscribes to Supabase realtime updates on `handoffs` and `tickets`.
2. New escalation appears instantly with full conversation context (no re-asking the customer).
3. Agent resolves the issue, updates ticket status, optionally replies directly in the conversation thread.

### 2.3 Knowledge base update flow

1. Admin uploads/updates docs (help center articles, PDFs, wiki exports).
2. `ingest_docs.py` script (or `POST /ingest`) chunks, embeds, and upserts into Qdrant.
3. Next customer query automatically benefits from updated content — no redeploy needed.

### 2.4 Sequence diagram (text form)

```
Customer          Next.js Widget       FastAPI          LangGraph Agent         Qdrant / Supabase / Claude
   │                    │                 │                     │                          │
   │── message ────────>│                 │                     │                          │
   │                    │── POST /chat ──>│                     │                          │
   │                    │                 │── invoke(state) ───>│                          │
   │                    │                 │                     │── embed + search ───────>│ (Qdrant)
   │                    │                 │                     │<── top-k chunks ──────────│
   │                    │                 │                     │── generate response ─────>│ (Claude)
   │                    │                 │                     │<── response ───────────────│
   │                    │                 │                     │── route (ticket/handoff) ─>│ (Supabase)
   │                    │                 │<── result ──────────│                          │
   │                    │<── response ────│                     │                          │
   │<── reply shown ────│                 │                     │                          │
```

---

## 3. System Architecture

```
                         ┌─────────────────────────────┐
                         │        Next.js Frontend      │
                         │  ┌───────────┐ ┌───────────┐ │
                         │  │Chat Widget│ │Admin Dash │ │
                         │  └───────────┘ └───────────┘ │
                         └───────────────┬───────────────┘
                                         │ HTTPS / SSE
                                         ▼
                         ┌─────────────────────────────┐
                         │         FastAPI Backend      │
                         │  /chat  /conversations        │
                         │  /tickets  /ingest             │
                         └───────────────┬───────────────┘
                                         │
                                         ▼
                         ┌─────────────────────────────┐
                         │      LangGraph Agent Graph    │
                         │                               │
                         │ classify_intent               │
                         │       ↓                       │
                         │ retrieve_context               │
                         │       ↓                       │
                         │ generate_response               │
                         │       ↓                       │
                         │ route_decision                  │
                         │     ↙        ↘                │
                         │ create_ticket   handoff          │
                         │     ↘        ↙                │
                         │       persist                    │
                         └──┬─────────┬─────────┬──────────┘
                            │         │         │
                            ▼         ▼         ▼
                       ┌────────┐ ┌────────┐ ┌──────────┐
                       │ Qdrant │ │Supabase│ │ Claude   │
                       │ (KB    │ │(convos,│ │ API      │
                       │ vectors)│ │tickets,│ │(reasoning│
                       │        │ │handoffs)│ │/generation)│
                       └────────┘ └────────┘ └──────────┘
```

---

## 4. Folder & File Structure

```
support-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app entrypoint, router registration
│   │   │
│   │   ├── api/                        # Route handlers
│   │   │   ├── chat.py                 # POST /chat
│   │   │   ├── conversations.py        # GET /conversations/{id}
│   │   │   ├── tickets.py              # GET/PATCH /tickets
│   │   │   └── ingest.py               # POST /ingest
│   │   │
│   │   ├── agent/                      # LangGraph agent core
│   │   │   ├── graph.py                # Graph definition & compilation
│   │   │   ├── nodes.py                # Node functions (classify, retrieve, generate, route, etc.)
│   │   │   ├── state.py                # AgentState TypedDict schema
│   │   │   └── prompts.py              # System prompts, intent classification prompts
│   │   │
│   │   ├── rag/                        # Retrieval-augmented generation utilities
│   │   │   ├── embed.py                # Embedding client wrapper
│   │   │   ├── retriever.py            # Qdrant query logic
│   │   │   └── chunker.py              # Text chunking logic
│   │   │
│   │   ├── db/                         # Data layer
│   │   │   ├── supabase_client.py      # Supabase client + query wrappers
│   │   │   └── models.py               # Pydantic models mirroring DB schema
│   │   │
│   │   └── core/                       # Cross-cutting concerns
│   │       ├── config.py               # Env var loading, settings
│   │       └── logging.py              # Structured logging setup
│   │
│   ├── tests/
│   │   ├── test_nodes.py
│   │   ├── test_api.py
│   │   └── test_retrieval.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── (widget)/
│   │   │   └── chat/
│   │   │       └── page.tsx            # Chat widget page
│   │   └── (admin)/
│   │       └── dashboard/
│   │           └── page.tsx            # Admin dashboard page
│   │
│   ├── components/
│   │   ├── ChatWindow.tsx              # Main chat UI container
│   │   ├── MessageBubble.tsx           # Individual message rendering
│   │   ├── TicketList.tsx              # Admin ticket table
│   │   └── HandoffQueue.tsx            # Admin escalation queue
│   │
│   ├── lib/
│   │   ├── api.ts                      # Fetch wrappers for backend calls
│   │   └── supabaseClient.ts           # Supabase client (realtime subscriptions)
│   │
│   ├── package.json
│   └── tailwind.config.ts
│
├── ingestion/
│   └── ingest_docs.py                  # Standalone KB ingestion script
│
├── docker-compose.yml                  # Local dev: Qdrant + backend + frontend
└── README.md
```

---

## 5. Component Responsibilities

| Component | Responsibility |
|---|---|
| `app/main.py` | Wires up FastAPI app, middleware, router registration |
| `app/api/*` | Thin route handlers — validate input, call agent/db, return response |
| `app/agent/graph.py` | Defines node order and conditional routing logic |
| `app/agent/nodes.py` | Actual logic for each step (classify, retrieve, generate, route, persist) |
| `app/rag/*` | Everything related to turning text into searchable vectors and querying them |
| `app/db/supabase_client.py` | All reads/writes to Postgres — single source of truth for DB access |
| `frontend/components/ChatWindow.tsx` | Renders conversation, handles streaming response display |
| `frontend/components/TicketList.tsx` / `HandoffQueue.tsx` | Admin-facing views into Supabase data |
| `ingestion/ingest_docs.py` | Reusable script/CI job to keep Qdrant KB current |

---

### Related documents
- PRD: `ai-support-agent-prd.md`
- TRD: `ai-support-agent-trd.md`
- Implementation Plan: `ai-support-agent-implementation-plan.md`
