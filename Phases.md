# Phases
## AI Customer Support Agent — Step-by-Step Build Guide

**Version:** 1.0
**Last updated:** July 27, 2026

This document breaks the project into sequential phases. Each phase lists concrete steps to complete before moving to the next. Phases build on each other — don't skip ahead.

---

## Phase 0: Project Setup

**Goal:** get all accounts, keys, and the repo skeleton ready.

1. Create OpenRouter API key (openrouter.ai/keys).
2. Create Qdrant Cloud account (or set up local Docker instance).
3. Create Supabase project, note URL and service role key.
4. Install Python 3.11+, Node.js 20+, Docker.
5. Initialize monorepo with `backend/`, `frontend/`, `ingestion/` folders (per architecture.md).
6. Create `.env` files for backend with all required keys.
7. Set up `requirements.txt` (backend) and `package.json` (frontend) with the libraries from `rules.md`.
8. Push initial empty scaffold to a git repo.

**Done when:** repo exists, all services reachable with a basic "hello world" ping (OpenRouter API test call, Qdrant connection test, Supabase connection test).

---

## Phase 1: Database Schema (Supabase)

**Goal:** the data layer is live before anything else is built on top of it.

1. Write and run SQL migrations for: `customers`, `conversations`, `messages`, `tickets`, `handoffs`.
2. Add indexes: `messages(conversation_id, created_at)`, `tickets(status)`, `conversations(status)`.
3. Enable Row-Level Security policies (even if permissive for now — tighten later).
4. Build `db/supabase_client.py` with functions:
   - `get_conversation_history(conversation_id)`
   - `save_message(conversation_id, role, content)`
   - `create_ticket(...)`
   - `create_handoff(...)`
   - `update_conversation_status(...)`
5. Write unit tests for each DB function against a test Supabase project or local Postgres.

**Done when:** you can create a conversation, add messages, create a ticket, and read them all back via the wrapper functions.

---

## Phase 2: Knowledge Base Ingestion (Qdrant)

**Goal:** company docs are searchable as vectors.

1. Collect sample company docs (help center articles, PDFs, FAQ pages).
2. Build `rag/chunker.py` — splits docs into ~500-token chunks with overlap.
3. Build `rag/embed.py` — wraps the embedding model (Voyage AI or OpenAI).
4. Create the Qdrant collection `kb_chunks` with the correct vector size and distance metric.
5. Write `ingestion/ingest_docs.py` to load → chunk → embed → upsert docs into Qdrant.
6. Run ingestion on your sample docs.
7. Build `rag/retriever.py` — takes a query, embeds it, returns top-k chunks from Qdrant.
8. Manually test retrieval: run a few sample questions, confirm relevant chunks come back.

**Done when:** querying the retriever with a real customer-style question returns correct, relevant chunks.

---

## Phase 3: LangGraph Agent Core

**Goal:** the agent can answer a question end-to-end (no routing/tickets yet).

1. Define `agent/state.py` — the `AgentState` schema.
2. Write `agent/prompts.py` — system prompt, intent classification prompt.
3. Build `agent/nodes.py`:
   - `classify_intent` (detect intent + language)
   - `retrieve_context` (calls `rag/retriever.py`)
   - `generate_response` (calls Claude with retrieved docs + history)
4. Wire up `agent/graph.py`: `classify_intent → retrieve_context → generate_response → END`.
5. Test the graph directly (no API layer yet) with sample inputs in a script or notebook.
6. Verify: agent grounds answers in retrieved docs, says "I don't know" when nothing relevant is found.

**Done when:** `agent.invoke(state)` returns a correct, grounded response for a handful of test questions.

---

## Phase 4: FastAPI Backend — Core Chat Endpoint

**Goal:** the agent is reachable over HTTP.

1. Build `app/main.py` — FastAPI app setup, CORS config, router registration.
2. Build `api/chat.py` — `POST /chat` endpoint:
   - Load history from Supabase.
   - Build `AgentState`.
   - Invoke the agent graph.
   - Persist messages.
   - Return response.
3. Add basic error handling (try/catch around agent invocation, graceful fallback message).
4. Add structured logging per request (`core/logging.py`).
5. Test with curl/Postman: send a message, get a response, confirm messages saved in Supabase.

**Done when:** you can have a full back-and-forth conversation via API calls, with memory persisting correctly.

---

## Phase 5: Ticketing & Escalation Logic

**Goal:** the agent knows when to create a ticket or hand off to a human.

1. Extend `agent/state.py` with `ticket_needed`, `escalate`, `confidence` fields.
2. Add `route_decision` node — rules for when to set `ticket_needed`/`escalate` (refund/billing → ticket; low confidence or explicit request → escalate; sensitive topics → forced escalate).
3. Add `create_ticket_node` — writes to `tickets` table via `db/supabase_client.py`.
4. Add `handoff_node` — writes to `handoffs` table, updates conversation status to `escalated`.
5. Update `agent/graph.py` with conditional edges after `route_decision`.
6. Add a notification hook (e.g. Slack webhook) fired on handoff.
7. Test scenarios: a billing question (should create ticket), a request for a human (should escalate), a sensitive topic (should force escalate).

**Done when:** tickets and handoffs are correctly created in Supabase for the right trigger conditions, and notifications fire.

---

## Phase 6: Multi-language & Memory Polish

**Goal:** the agent handles long conversations and non-English customers well.

1. Add language detection to `classify_intent`.
2. Update `generate_response` prompt to always reply in the detected language.
3. Implement rolling summary: after N messages, summarize older history into `conversations.summary`, only pass recent messages + summary to Claude (not full history).
4. Test with a long conversation (20+ turns) — confirm context is preserved without ballooning token usage.
5. Test in at least 2–3 non-English languages relevant to your customer base.

**Done when:** long conversations stay coherent and cost-efficient, and non-English queries get accurate same-language responses.

---

## Phase 7: Frontend — Chat Widget

**Goal:** customers have a real UI to talk to the agent.

1. Scaffold Next.js app (`frontend/`), set up Tailwind.
2. Build `lib/api.ts` — fetch wrapper for `POST /chat` (with streaming support if using SSE).
3. Build `components/MessageBubble.tsx` — renders a single message.
4. Build `components/ChatWindow.tsx` — message list, input box, send handling, loading/typing state.
5. Build `app/(widget)/chat/page.tsx` — wires it together, manages `conversation_id` in local state.
6. Style to match brand (or a clean default) — see `frontend-design` conventions.
7. Manual QA: full conversation flow in the browser, including a scenario that triggers a ticket and one that triggers escalation.

**Done when:** a real user can have a full conversation in the browser and see appropriate behavior for tickets/escalation.

---

## Phase 8: Frontend — Admin Dashboard

**Goal:** support managers/agents can see and act on tickets and handoffs.

1. Build `lib/supabaseClient.ts` for realtime subscriptions.
2. Build `components/TicketList.tsx` — table of tickets with status/priority filters.
3. Build `components/HandoffQueue.tsx` — live-updating list of escalated conversations.
4. Build `app/(admin)/dashboard/page.tsx` — combines both, plus a conversation viewer (full transcript).
5. Add basic auth gate (Supabase Auth) so only admins can access this route.
6. Manual QA: trigger an escalation from the chat widget, confirm it appears in the dashboard in real time.

**Done when:** an admin can log in, see live tickets and escalations, and view full conversation context for each.

---

## Phase 9: Testing & Evaluation

**Goal:** confidence that the agent performs well before real traffic.

1. Write unit tests for each agent node (mocked Claude/Qdrant/Supabase calls).
2. Write integration tests for the full `/chat` flow.
3. Build a 50+ question eval set from real KB content; track accuracy, hallucination rate, retrieval relevance.
4. Run load tests against `/chat` to confirm latency targets hold under concurrent load.
5. Fix any issues surfaced before moving to deployment.

**Done when:** eval suite passes target thresholds (see PRD metrics section) and load tests meet latency/throughput requirements.

---

## Phase 10: Deployment

**Goal:** the product is live.

1. Dockerize the FastAPI backend.
2. Deploy backend to Fly.io/Railway/Render with production env vars.
3. Deploy frontend to Vercel.
4. Point Qdrant client and Supabase client at production instances (separate from dev/staging).
5. Set up monitoring/alerting (error rate, latency, escalation rate spikes).
6. Run a staged rollout: alpha (internal only) → beta (limited customer subset) → GA (full rollout), per the PRD rollout plan.

**Done when:** the agent is handling real customer conversations in production, with monitoring in place to catch issues early.

---

## Phase Summary Table

| Phase | Focus |
|---|---|
| 0 | Project setup, accounts, repo skeleton |
| 1 | Supabase schema + DB wrapper functions |
| 2 | Qdrant ingestion pipeline |
| 3 | LangGraph agent core (classify → retrieve → generate) |
| 4 | FastAPI `/chat` endpoint, memory working end-to-end |
| 5 | Ticketing + escalation logic |
| 6 | Multi-language + long-conversation memory polish |
| 7 | Chat widget frontend |
| 8 | Admin dashboard frontend |
| 9 | Testing + evaluation |
| 10 | Deployment |

---

### Related documents
- PRD: `ai-support-agent-prd.md`
- TRD: `ai-support-agent-trd.md`
- Architecture: `architecture.md`
- Rules: `rules.md`
