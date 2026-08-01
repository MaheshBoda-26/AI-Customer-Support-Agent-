# Rules
## AI Customer Support Agent

**Version:** 1.0
**Last updated:** July 27, 2026

This document defines the working rules for the project: what we use, what we avoid, error handling standards, and the boundaries of what the AI agent is allowed to do.

---

## 1. What We Use

### Backend
- **Python 3.11+** for all backend code.
- **FastAPI** for the API layer. Thin route handlers only, business logic lives in `agent/` and `db/`.
- **LangGraph** for agent orchestration. Every agent decision path is an explicit node/edge, not buried in a single prompt.
- **Pydantic** for all request/response validation and internal data models.
- **OpenRouter (Claude models)** as the LLM provider. Use a cheaper model (e.g. Haiku-class) for classification tasks, the primary model for generation. Access via OpenAI-compatible API.
- **Qdrant** as the only vector store.
- **Supabase (Postgres)** as the only relational store, and the source of truth for conversations, tickets, handoffs, and customers.
- **Structured (JSON) logging** for every agent node execution.
- **pytest** for all backend tests.

### Frontend
- **Next.js (App Router)** with **React** and **TypeScript**. No plain JavaScript files.
- **Tailwind CSS** for styling. No inline style objects except for dynamic values.
- **Supabase JS client** for realtime subscriptions (tickets, handoffs) on the admin dashboard.
- **Zod** for validating any data crossing the frontend/backend boundary.

### Infra
- **Docker** for local dev parity and backend deployment.
- Environment variables for all secrets and config — never hardcoded values.

---

## 2. What We Avoid

- **No mixing vector stores.** Qdrant only. Don't introduce Pinecone, Weaviate, or pgvector alongside it.
- **No mixing relational stores.** Supabase only. Don't add a second database "just for this one feature."
- **No business logic in route handlers.** `api/*.py` files call into `agent/` or `db/` — they don't contain decision logic themselves.
- **No hardcoded prompts scattered across the codebase.** All prompts live in `agent/prompts.py`.
- **No silent failures.** Every external call (Claude, Qdrant, Supabase) that fails must be caught, logged, and result in either a retry or a clear fallback — never a swallowed exception.
- **No client-side secrets.** API keys and service role keys never ship to the frontend bundle.
- **No unbounded conversation history.** Don't pass the entire message history to Claude on every call — use the sliding window + summary approach defined in the TRD.
- **No answers without retrieval grounding.** The agent doesn't generate substantive factual answers without first checking the KB, unless the query is clearly conversational (e.g. greetings).
- **No new libraries added without checking for an existing equivalent already in the stack.** Don't add a second HTTP client, a second state management library, etc.
- **No `any` types in TypeScript.** Type everything crossing an API boundary.

---

## 3. Libraries (Reference List)

### Backend (Python)
```
fastapi
uvicorn[standard]
pydantic
openai
langgraph
langchain-text-splitters
qdrant-client
supabase
python-dotenv
unstructured
voyageai
httpx
tenacity
pytest
pytest-asyncio
```

### Frontend (Node)
```
next
react
tailwindcss
@supabase/supabase-js
zod
@tanstack/react-query (or swr)
lucide-react
```

Any addition to this list requires a one-line justification in the PR description: what it does, and why nothing on this list already covers it.

---

## 4. Error Handling Rules

| Situation | Rule |
|---|---|
| Claude API call fails (timeout, rate limit) | Retry with exponential backoff (`tenacity`, max 3 attempts). On final failure, return a graceful fallback message to the customer and log the error. |
| Qdrant query fails | Retry once. On failure, proceed without retrieved context but flag `retrieval_failed=True` in state so the agent lowers confidence and is more likely to escalate. |
| Supabase write fails | Retry once. On failure, log the error with full context (conversation_id, payload) for manual recovery — never lose a customer's message silently. |
| Malformed/unexpected LLM output (e.g. broken JSON from a structured prompt) | Catch the parse error, retry the call once with a stricter prompt. If it fails again, fall back to a safe default (e.g. `escalate=True`) rather than guessing. |
| Any unhandled exception in the agent graph | Caught at the top level in the `/chat` handler. Customer sees a generic "something went wrong" message. Full stack trace logged internally. Never expose internal errors or stack traces to the customer. |
| Rate limiting / abuse | Per-IP and per-customer request limits on `/chat`. Excess requests get a clear rate-limit response, not a silent drop. |

**General principle:** fail loud internally (logs, alerts), fail soft externally (customer never sees a raw error or a broken conversation).

---

## 5. Boundaries of the AI Agent

### The agent MUST:
- Ground factual answers in retrieved KB content. If nothing relevant is retrieved, say so rather than guessing.
- Escalate to a human when confidence is low, when explicitly asked, or when the topic is sensitive (legal, security, financial disputes, account deletion).
- Stay within the support domain. It does not answer unrelated general-knowledge questions, write code, or perform tasks outside customer support.
- Preserve conversation context accurately — never fabricate details the customer didn't provide.
- Respect the customer's language and reply in kind.

### The agent MUST NOT:
- Invent policies, refund terms, pricing, or promises not present in the knowledge base.
- Make final decisions on refunds, account bans, legal claims, or anything with binding consequence — it can inform and create a ticket, but a human approves the action.
- Pretend to be a human when directly asked if it's an AI.
- Continue looping on a failed resolution indefinitely — hard cap on retry attempts before forced escalation.
- Access or modify customer account data beyond what's needed to answer the current, in-scope question.
- Store or repeat sensitive data (passwords, full payment card numbers) even if a customer pastes it into chat — flag and redact instead.

### Escalation is mandatory, not optional, when:
- Customer explicitly asks for a human.
- Confidence score falls below the defined threshold.
- Topic is classified as legal, security incident, account deletion, or payment dispute.
- The same issue has failed to resolve after N attempts within one conversation.

---

### Related documents
- PRD: `ai-support-agent-prd.md`
- TRD: `ai-support-agent-trd.md`
- Architecture: `architecture.md`
- Implementation Plan: `ai-support-agent-implementation-plan.md`
