# Technical Requirements Document (TRD)
## AI Customer Support Agent

**Version:** 1.0
**Status:** Draft
**Owner:** [Your name]
**Last updated:** July 27, 2026

---

## 1. Purpose

This document defines the technical requirements for the AI Customer Support Agent. It covers system architecture, tech stack, libraries, data models, APIs, infrastructure, security, and performance requirements needed to build and operate the product described in the PRD.

---

## 2. System Architecture

```
Next.js (chat widget + admin dashboard)
        │  HTTPS / REST / SSE
        ▼
FastAPI backend
   ├── /chat        → LangGraph agent invocation
   ├── /conversations
   ├── /tickets
   └── /ingest
        │
        ▼
LangGraph Agent Graph
   classify_intent → retrieve_context → generate_response
        → route_decision → (create_ticket | handoff) → persist
        │                │                    │
        ▼                ▼                    ▼
   Claude API         Qdrant               Supabase
  (reasoning /      (vector search        (Postgres:
   generation)        over KB chunks)      conversations,
                                            messages, tickets,
                                            handoffs, customers)
```

**Deployment topology:**
- Frontend: Vercel (Next.js, edge-served)
- Backend: containerized FastAPI on Fly.io / Railway / Render
- Qdrant: Qdrant Cloud (managed) or self-hosted container
- Supabase: managed Postgres + Auth + Realtime

---

## 3. Tech Stack & Libraries

### 3.1 Core Stack

| Layer | Technology | Version (min) |
|---|---|---|
| LLM | OpenRouter (Claude models) | claude-3.5-sonnet / claude-3-haiku for cheap tasks |
| Agent orchestration | LangGraph | 0.2.x |
| Vector DB | Qdrant | 1.9+ |
| Relational DB / Auth / Realtime | Supabase (Postgres 15) | — |
| Backend framework | FastAPI | 0.111+ |
| Frontend framework | Next.js | 14+ (App Router) |
| Runtime | Python | 3.11+ |
| Runtime | Node.js | 20+ |

### 3.2 Backend Python Libraries

```
fastapi==0.111.*
uvicorn[standard]==0.30.*
pydantic==2.*
openai==1.*
langgraph==0.2.*
langchain-text-splitters==0.2.*
qdrant-client==1.9.*
supabase==2.*
python-dotenv==1.*
unstructured==0.14.*        # doc parsing for ingestion
voyageai==0.2.*             # embeddings (or openai==1.* for embeddings alt)
httpx==0.27.*
tenacity==8.*               # retry logic for external calls
pytest==8.*
pytest-asyncio==0.23.*
```

### 3.3 Frontend Libraries

```
next@14
react@18
tailwindcss@3
@supabase/supabase-js@2
zod                          # request/response validation
swr or @tanstack/react-query # data fetching/caching
lucide-react                 # icons
```

### 3.4 Embeddings & Retrieval

- Embedding model: `voyage-3` (recommended pairing with Claude) or `text-embedding-3-small` (OpenAI) as an alternative.
- Vector size: 1024 (voyage-3) — must match Qdrant collection config.
- Chunking: `RecursiveCharacterTextSplitter`, chunk size ~500 tokens, overlap ~50 tokens.
- Retrieval: top-k = 5 by default, cosine similarity, configurable per query.

---

## 4. Data Model

### 4.1 Supabase (Postgres) Schema

```sql
create table customers (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  name text,
  created_at timestamptz default now()
);

create table conversations (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid references customers(id),
  status text default 'active',        -- active | escalated | closed
  language text default 'en',
  summary text,                        -- rolling summary for long convos
  created_at timestamptz default now()
);

create table messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references conversations(id),
  role text check (role in ('user','assistant','system')),
  content text,
  created_at timestamptz default now()
);

create table tickets (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references conversations(id),
  subject text,
  description text,
  category text,                       -- billing | bug | account | other
  status text default 'open',          -- open | in_progress | resolved
  priority text default 'normal',      -- low | normal | high | urgent
  created_at timestamptz default now()
);

create table handoffs (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references conversations(id),
  reason text,
  assigned_to text,
  created_at timestamptz default now()
);
```

Indexes: `messages(conversation_id, created_at)`, `tickets(status)`, `conversations(status)`.

### 4.2 Qdrant Collection

```
Collection: kb_chunks
Vector size: 1024
Distance: Cosine
Payload schema:
  - text: string
  - source: string        (doc filename/URL)
  - doc_title: string
  - section: string
  - language: string
  - updated_at: string (ISO date)
```

---

## 5. Agent State Schema (LangGraph)

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

Nodes: `classify_intent`, `retrieve_context`, `generate_response`, `route_decision`, `create_ticket_node`, `handoff_node`, `persist_node`.

Model tiering: `classify_intent` uses a cheaper/faster Claude model; `generate_response` uses the primary model for quality.

---

## 6. API Specification

### 6.1 `POST /chat`
**Request:**
```json
{
  "conversation_id": "uuid | null",
  "customer_id": "uuid | null",
  "message": "string"
}
```
**Response:**
```json
{
  "conversation_id": "uuid",
  "response": "string",
  "ticket_created": false,
  "escalated": false
}
```
Supports `Accept: text/event-stream` for streamed token-by-token response.

### 6.2 `GET /conversations/{id}`
Returns full message history + conversation metadata.

### 6.3 `GET /tickets`
Query params: `status`, `priority`, `category`. Returns paginated ticket list.

### 6.4 `PATCH /tickets/{id}`
Update ticket `status`/`priority` (admin only).

### 6.5 `POST /ingest`
Protected (admin/service token). Triggers KB re-ingestion from a docs source.

**Auth:** Bearer token (Supabase Auth JWT) for admin endpoints; public endpoints (`/chat`) rate-limited by IP/session.

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Latency | First-token < 2s, full response < 6s (95th percentile) |
| Throughput | Support 100+ concurrent conversations at launch, horizontally scalable |
| Availability | 99.5% uptime target |
| Rate limiting | Per-IP and per-customer limits on `/chat` to prevent abuse |
| Logging | Structured logs (JSON) per agent node: intent, retrieval hits, routing decision, latency |
| Error handling | Retry with backoff (`tenacity`) on Claude/Qdrant/Supabase transient failures; graceful fallback message to customer on hard failure |
| Cost tracking | Log token usage per conversation; dashboard for daily spend |

---

## 8. Security Requirements

- All secrets (OpenRouter API key, Supabase service key, Qdrant API key) stored in platform secret managers, never in client code or repo.
- Supabase Row-Level Security enabled on all customer-facing tables; service role key used only server-side.
- TLS enforced on all endpoints.
- Input sanitization on all user-submitted text before storage/display (prevent stored XSS in admin dashboard).
- PII fields (email, name) encrypted at rest where supported; access limited to authenticated admin roles.
- Audit log for admin actions (ticket updates, KB re-ingestion).

---

## 9. Testing Requirements

| Test type | Scope |
|---|---|
| Unit tests | Each LangGraph node in isolation (mocked Claude/Qdrant/Supabase calls) |
| Integration tests | Full `/chat` flow against a test Qdrant collection + test Supabase schema |
| Eval suite | 50+ curated Q&A pairs from real KB; track accuracy, hallucination rate, retrieval relevance |
| Load tests | Concurrent `/chat` requests (e.g. Locust) to validate latency targets under load |
| Regression tests | Run eval suite on every prompt/model change before deploy |

---

## 10. Deployment & Environments

| Environment | Purpose |
|---|---|
| `dev` | Local development, Docker Compose for Qdrant + local Supabase (or shared dev project) |
| `staging` | Pre-production, connected to staging Supabase project + staging Qdrant collection |
| `production` | Live traffic, separate Supabase project, production Qdrant collection, monitoring enabled |

CI/CD: run unit + integration tests on every PR; deploy to staging on merge to `main`; manual promotion to production.

---

## 11. Monitoring & Observability

- Request/response logging per `/chat` call (latency, tokens used, node path taken).
- Alerting on: error rate spike, latency SLA breach, escalation rate spike, Claude/Qdrant/Supabase downtime.
- Dashboard metrics: deflection rate, escalation rate, average tokens/conversation, ticket volume by category.

---

### Related documents
- PRD: `ai-support-agent-prd.md`
- Implementation Plan: `ai-support-agent-implementation-plan.md`
