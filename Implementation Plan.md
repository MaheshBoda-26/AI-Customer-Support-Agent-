# AI Customer Support Agent — Implementation Plan

Tech stack: **Claude · LangGraph · Qdrant · Supabase · FastAPI · Next.js**

---

## 0. Architecture Overview

```
Customer (Next.js widget)
        |
        v
   FastAPI (/chat)
        |
        v
   LangGraph Agent Graph
   ┌─────────────────────────────────────────────┐
   │ classify_intent → retrieve_context →         │
   │ generate_response → route (ticket/handoff) → │
   │ persist_and_respond                          │
   └─────────────────────────────────────────────┘
        |             |                |
        v             v                v
     Qdrant       Supabase         Claude API
   (doc chunks)  (memory, tickets, (reasoning /
                  users, sessions)  generation)
```

Repo layout (monorepo, simplest for solo/small-team build):

```
support-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   ├── tickets.py
│   │   │   └── ingest.py
│   │   ├── agent/
│   │   │   ├── graph.py           # LangGraph definition
│   │   │   ├── nodes.py           # node functions
│   │   │   ├── state.py           # AgentState schema
│   │   │   └── prompts.py
│   │   ├── rag/
│   │   │   ├── embed.py
│   │   │   ├── retriever.py
│   │   │   └── chunker.py
│   │   ├── db/
│   │   │   ├── supabase_client.py
│   │   │   └── models.py
│   │   └── core/
│   │       ├── config.py
│   │       └── logging.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── (widget)/chat/page.tsx
│   │   └── (admin)/dashboard/page.tsx
│   ├── components/
│   │   ├── ChatWindow.tsx
│   │   ├── MessageBubble.tsx
│   │   └── TicketList.tsx
│   ├── lib/api.ts
│   └── package.json
├── ingestion/
│   └── ingest_docs.py              # one-off/CI script for KB updates
└── docker-compose.yml
```

---

## 1. Environment & Accounts Setup (Day 0)

1. **OpenRouter API key** — openrouter.ai/keys → create key.
2. **Qdrant** — either Qdrant Cloud (free tier) or `docker run -p 6333:6333 qdrant/qdrant`.
3. **Supabase** — create project at supabase.com, grab `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
4. **Node.js 20+**, **Python 3.11+**, **Docker**.

`.env` (backend):
```
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_FAST_MODEL=anthropic/claude-3-haiku
QDRANT_URL=
QDRANT_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
EMBEDDING_MODEL=voyage-3        # or openai text-embedding-3-small
```

---

## 2. Phase 1 — Supabase Schema (Memory, Tickets, Users)

Tables:

```sql
-- customers/users
create table customers (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  name text,
  created_at timestamptz default now()
);

-- conversation sessions
create table conversations (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid references customers(id),
  status text default 'active',       -- active | escalated | closed
  language text default 'en',
  created_at timestamptz default now()
);

-- individual messages (conversation memory)
create table messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references conversations(id),
  role text check (role in ('user','assistant','system')),
  content text,
  created_at timestamptz default now()
);

-- support tickets
create table tickets (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references conversations(id),
  subject text,
  description text,
  status text default 'open',        -- open | in_progress | resolved
  priority text default 'normal',
  created_at timestamptz default now()
);

-- escalation/handoff log
create table handoffs (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references conversations(id),
  reason text,
  assigned_to text,
  created_at timestamptz default now()
);
```

Libraries: `supabase-py` (backend), row-level security policies later once you add real auth.

**Deliverable:** schema deployed, `supabase_client.py` wrapper with `get_conversation_history()`, `save_message()`, `create_ticket()`.

---

## 3. Phase 2 — Knowledge Base Ingestion (Qdrant)

Purpose: turn company docs (PDF, Markdown, HTML help center, Notion export) into searchable vectors.

Libraries:
```
qdrant-client
langchain-text-splitters   # for chunking
unstructured               # or pypdf / markdown parsers for raw extraction
voyageai   (or openai)     # embeddings
```

Steps:
1. **Load** raw docs → plain text (`unstructured.partition.auto`).
2. **Chunk** with `RecursiveCharacterTextSplitter` (chunk_size ~500 tokens, overlap ~50).
3. **Embed** each chunk (Voyage AI's `voyage-3` embeddings pair well with Claude, or OpenAI `text-embedding-3-small` if you prefer).
4. **Upsert** into Qdrant collection `kb_chunks` with payload: `{text, source, doc_title, section}`.
5. Store one Qdrant collection per company/tenant if multi-tenant later.

```python
# ingestion/ingest_docs.py (sketch)
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
client.recreate_collection(
    collection_name="kb_chunks",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
)

for chunk in chunks:
    vector = embed(chunk.text)
    client.upsert(collection_name="kb_chunks", points=[
        PointStruct(id=chunk.id, vector=vector, payload={"text": chunk.text, "source": chunk.source})
    ])
```

**Deliverable:** re-runnable ingestion script; can be triggered manually or on a schedule/CI when docs change.

---

## 4. Phase 3 — LangGraph Agent Core

Libraries:
```
langgraph
openai     # OpenRouter uses OpenAI-compatible API
```

### 4.1 Define state

```python
# app/agent/state.py
from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    conversation_id: str
    messages: List[dict]          # chat history
    user_input: str
    retrieved_docs: List[str]
    intent: Optional[str]         # question | complaint | refund_request | other
    confidence: float
    ticket_needed: bool
    escalate: bool
    response: str
```

### 4.2 Nodes

- `classify_intent` — small Claude call (or Haiku for cost) to tag intent + detect language.
- `retrieve_context` — embed `user_input`, query Qdrant top-k (e.g. 5), attach to state.
- `generate_response` — main Claude call with system prompt + retrieved docs + last N messages.
- `route_decision` — rule + confidence based: if intent == refund/billing → `ticket_needed=True`; if confidence < threshold or user explicitly asks for a human → `escalate=True`.
- `create_ticket_node` — writes to Supabase `tickets` table if `ticket_needed`.
- `handoff_node` — writes to `handoffs` table, flips conversation `status` to `escalated`.
- `persist_node` — saves user + assistant messages to `messages` table.

### 4.3 Graph wiring

```python
# app/agent/graph.py
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)
graph.add_node("classify_intent", classify_intent)
graph.add_node("retrieve_context", retrieve_context)
graph.add_node("generate_response", generate_response)
graph.add_node("route_decision", route_decision)
graph.add_node("create_ticket", create_ticket_node)
graph.add_node("handoff", handoff_node)
graph.add_node("persist", persist_node)

graph.set_entry_point("classify_intent")
graph.add_edge("classify_intent", "retrieve_context")
graph.add_edge("retrieve_context", "generate_response")
graph.add_edge("generate_response", "route_decision")

graph.add_conditional_edges(
    "route_decision",
    lambda s: "ticket" if s["ticket_needed"] else ("handoff" if s["escalate"] else "persist"),
    {"ticket": "create_ticket", "handoff": "handoff", "persist": "persist"}
)
graph.add_edge("create_ticket", "persist")
graph.add_edge("handoff", "persist")
graph.add_edge("persist", END)

agent = graph.compile()
```

**Deliverable:** `agent.invoke(state)` runs end-to-end for one message.

---

## 5. Phase 4 — FastAPI Backend

Libraries:
```
fastapi
uvicorn
pydantic
supabase-py
python-dotenv
```

Endpoints:
| Method | Path | Purpose |
|---|---|---|
| POST | `/chat` | send message, get agent response (stream optional) |
| GET | `/conversations/{id}` | fetch history |
| GET | `/tickets` | list tickets (admin) |
| PATCH | `/tickets/{id}` | update ticket status |
| POST | `/ingest` | trigger KB re-ingestion (admin/protected) |

```python
# app/api/chat.py
@router.post("/chat")
async def chat(payload: ChatRequest):
    history = get_conversation_history(payload.conversation_id)
    state = {
        "conversation_id": payload.conversation_id,
        "messages": history,
        "user_input": payload.message,
        ...
    }
    result = agent.invoke(state)
    return {"response": result["response"], "ticket_created": result["ticket_needed"]}
```

For real-time feel, use `StreamingResponse` with Claude's streaming API in `generate_response`.

**Deliverable:** backend runnable locally (`uvicorn app.main:app --reload`), testable via curl/Postman.

---

## 6. Phase 5 — Human-like Conversation & Memory Tuning

- System prompt: define persona, tone, escalation rules, refusal boundaries (don't invent policies not in KB).
- Sliding window: pass last ~10–15 messages verbatim; summarize older history into a rolling summary field stored in `conversations` (a `summary` column updated periodically) to keep context small and cheap.
- Multi-language: detect language in `classify_intent`, instruct Claude to respond in the same language; keep KB in English but let Claude translate contextually, or maintain per-language KB collections if quality demands it.

---

## 7. Phase 6 — Human Handoff

- When `escalate=True`, mark conversation `status='escalated'`.
- Notify a human channel — simplest: Slack webhook or email via a `notify.py` util; more robust: push into a real helpdesk (Zendesk/Intercom API) as a follow-up integration.
- Admin dashboard (Next.js) polls/subscribes to `handoffs` table (Supabase real-time) so agents see new escalations live.

---

## 8. Phase 7 — Next.js Frontend

Libraries:
```
next, react
@supabase/supabase-js   (if reading realtime data client-side)
tailwindcss
```

Two surfaces:
1. **Chat widget** (`/chat`) — embeddable component, calls `POST /chat`, renders streaming response, shows typing indicator.
2. **Admin dashboard** (`/dashboard`) — ticket list, escalation queue, conversation viewer (read from Supabase directly via `supabase-js` with RLS, or via FastAPI).

**Deliverable:** working chat UI talking to local FastAPI backend end-to-end.

---

## 9. Phase 8 — Testing & Evaluation

- Unit tests per node (`pytest`) — mock Claude/Qdrant calls.
- Build a small eval set (20–50 real Q&A pairs from your docs) and score retrieval relevance + answer correctness before/after prompt changes.
- Load test `/chat` with concurrent requests (Locust or simple asyncio script).

---

## 10. Phase 9 — Deployment

- **Backend**: Dockerize FastAPI, deploy to Fly.io / Railway / Render.
- **Frontend**: Vercel (native Next.js support).
- **Qdrant**: Qdrant Cloud managed instance.
- **Supabase**: already managed/hosted.
- Add env-based config for prod vs dev, secrets via platform secret managers (never commit `.env`).

---

## 11. Suggested Build Order (Milestones)

| Milestone | Scope |
|---|---|
| M1 | Supabase schema + backend DB wrapper functions |
| M2 | Qdrant ingestion pipeline working on sample docs |
| M3 | LangGraph agent: intent → retrieve → generate (no routing yet) |
| M4 | FastAPI `/chat` endpoint wired to agent, manual curl testing |
| M5 | Add routing: ticket creation + escalation nodes |
| M6 | Next.js chat widget hitting `/chat` |
| M7 | Admin dashboard for tickets/handoffs |
| M8 | Multi-language + memory summarization polish |
| M9 | Testing, eval set, deploy |

---

### Suggested next step
Start with **M1 (Supabase schema)** and **M2 (Qdrant ingestion)** in parallel since they're independent — then M3 (LangGraph core) ties them together. I can scaffold the actual code for any milestone whenever you're ready — just say which one.
