# Document Copilot Implementation Checklist

**Goal:** Deploy a grounded document search assistant for Driftwood Capital analysts. Trust is everything — every answer must cite retrieved sources, never invent facts.

**Success metric:** Pilot group (5 senior analysts) saves ≥3 hours per analyst per week.

---

## Phase 1: Foundation (Backend Setup)

### Database & Schema
- [x] **Create Supabase project** — set up hosted Postgres, obtain connection strings and API keys
- [x] **SQLAlchemy models** — define `profiles`, `chat_threads`, `chat_messages`, `message_citations`, `source_documents`, `document_chunks` in `backend/app/database/models.py`
- [x] **Create pgvector extension** — ensure Supabase Postgres has vector support enabled
- [x] **Initial Alembic migration** — generate and apply schema for all tables, indexes (semantic + full-text), and RLS policies
- [x] **Add embedding column** — vector(1536) for OpenAI embeddings, plus tsvector for full-text search
- [x] **Test database connection** — verify SQLAlchemy can connect and execute queries against Supabase

### Backend Scaffolding
- [x] **FastAPI app structure** — set up `main.py`, router modules, middleware (CORS, error handling)
- [x] **Configuration module** — `app/config.py` reads all env vars (Supabase keys, OpenAI key, database URL) and validates on startup
- [x] **Supabase client factory** — `app/database/supabase.py` creates user-scoped and admin clients
- [x] **Dependencies module** — `app/auth/dependencies.py` for current user extraction

---

## Phase 2: Authentication & API Infrastructure

### Auth Integration
- [ ] **Supabase Auth verification** — `AuthService` validates `Authorization: Bearer <token>` at FastAPI boundary
- [ ] **JWT verification endpoint** — call Supabase Auth or validate signing keys locally
- [ ] **User creation** — link Supabase `auth.users.id` to `profiles` table on first login
- [ ] **Route protection** — add `@require_auth` dependency to restricted endpoints

### API Client (Backend)
- [ ] **Chat persistence layer** — `app/database/chats.py` for create/read/list chat threads and messages
- [ ] **Document persistence layer** — `app/database/documents.py` for storing source docs, chunks, embeddings
- [ ] **Citation persistence** — `app/database/chats.py` stores `message_citations` records

---

## Phase 3: Chat API (Stubbed)

### Streaming Endpoint
- [ ] **POST /chat/stream** — accept thread ID + messages, verify user owns thread, return streamed response
- [ ] **Request/response types** — Pydantic models for message format, streaming events
- [ ] **Stub assistant response** — hardcoded "answer not yet implemented" to test streaming plumbing
- [ ] **Error handling** — 401 for auth failure, 403 for access violation, 404 for missing thread
- [ ] **Chat creation endpoint** — POST /threads to create new chat thread

---

## Phase 4: Frontend Scaffolding (in parallel with Phase 3)

### React SPA Setup
- [ ] **Vite project** — `frontend/` with React + TypeScript
- [ ] **Routing** — React Router with `/` (home), `/chat/:threadId` (chat view), `/login` (auth)
- [ ] **Environment config** — `src/lib/env.ts` reads and validates `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [ ] **Supabase client** — `src/lib/supabase.ts` initializes browser Supabase instance
- [ ] **HTTP client** — `src/lib/http.ts` wraps fetch, injects auth token, handles errors

### Auth UI
- [ ] **Supabase Auth** — sign in with email (Driftwood email)
- [ ] **Session management** — store JWT in Supabase session, provide logout
- [ ] **Route guards** — redirect unauthenticated users to login

---

## Phase 5: Frontend + Backend Integration

### Chat UI (with Vercel AI SDK)
- [ ] **Install Vercel AI SDK** — @vercel/ai for chat components and streaming client
- [ ] **useChat hook** — initialize with thread ID, message history, endpoint = `/chat/stream`
- [ ] **Message display** — render user and assistant messages, show loading state
- [ ] **Send message** — capture user input, post to backend, stream response to UI
- [ ] **Thread list** — display user's past chat threads on home page

### Backend Chat Orchestration
- [ ] **Orchestrator module** — `app/chat/orchestrator.py` coordinates one turn end-to-end
- [ ] **Message conversion** — convert Vercel AI SDK message format to internal types
- [ ] **Streaming logic** — emit text deltas and structured events via SSE or chunked response

---

## Phase 6: Document Ingestion

### Corpus Preparation
- [ ] **Download SEC filings** — use `data/download.py` to fetch 10-K from EDGAR for sample companies (Netflix, Tesla, Costco, JPMorgan, United Healthcare, 2021–2025)
- [ ] **Parse to Markdown** — convert HTML/XML filings to normalized Markdown, extract metadata (ticker, CIK, filing date, accession number)
- [ ] **Store source documents** — persist normalized Markdown in `source_documents` table
- [ ] **Test with sample corpus** — verify parsing and storage work

### Chunking & Embeddings
- [ ] **Chunking logic** — split documents into semantic chunks (~500 tokens), preserve metadata (page/section, original offset)
- [ ] **OpenAI embeddings** — call OpenAI embedding API for each chunk, store 1536-dim vectors in `document_chunks.embedding`
- [ ] **Full-text search vectors** — generate tsvector for lexical search in `document_chunks.search_vector`
- [ ] **Batch ingestion** — load all chunks and vectors into Supabase in one batch

---

## Phase 7: Retrieval

### Semantic Search
- [ ] **Embed user query** — call OpenAI embedding API with user's question
- [ ] **pgvector retrieval** — semantic search on `document_chunks.embedding` (nearest k neighbors)
- [ ] **Hybrid search** — also run Postgres full-text search on `document_chunks.search_vector`

### Retrieval Service
- [ ] **Reciprocal Rank Fusion** — fuse semantic + lexical ranked lists into one ranked result set
- [ ] **Fetch context** — retrieve chunk text, metadata, and neighboring chunks for grounding
- [ ] **Retrieval tests** — unit tests verify RRF fusion, chunk fetching, and metadata preservation

---

## Phase 8: LLM Orchestration (PydanticAI)

### Agent Definition
- [ ] **Agent module** — `app/assistant/agent.py` defines PydanticAI agent with typed inputs/outputs
- [ ] **Dependencies** — `app/assistant/deps.py` bundles retriever, user_id, thread_id, etc.
- [ ] **Output types** — `GroundedAnswer`, `Citation`, `SourcePassage` Pydantic models
- [ ] **System instructions** — `app/assistant/instructions.md` encodes the grounding contract (cite everything, never invent, show confidence limits)

### Agent Tools
- [ ] **search_filings** — takes user question, returns ranked chunks via retriever
- [ ] **read_chunk** — reads full chunk text by ID
- [ ] **read_surrounding** — fetches neighboring chunks for context
- [ ] **Tool constraints** — agent can only cite chunks that were retrieved for this query

---

## Phase 9: Grounding & Citation

### Citation Validator
- [ ] **Grounding module** — `app/grounding/validator.py` checks all citations map to retrieved passages
- [ ] **Citation extraction** — parse assistant output, extract claimed citations
- [ ] **Validation logic** — ensure every citation is in the retrieved set, has source document, has page/section metadata
- [ ] **Fail on invalid** — return 502 or controlled error if grounding validation fails

### Grounding Tests
- [ ] **Unit tests** — citation extraction, metadata preservation, validation pass/fail scenarios
- [ ] **Integration tests** — full turn with retrieval → agent → citation → validation

---

## Phase 10: Full Chat Loop

### End-to-End Flow
- [ ] **Orchestrate one turn** — receive user message → retrieve → invoke agent → validate citations → stream response → persist to DB
- [ ] **Persist chat** — save user message, assistant message, cited chunks to database
- [ ] **Error recovery** — if LLM call fails, return error event, don't persist half-message
- [ ] **Streaming events** — send text deltas, then citations/source passages once generation completes

### Frontend Citation UI
- [ ] **Citation display** — inline clickable citations in answer text
- [ ] **Source passage modal** — show full passage, company/ticker/filing date/page on hover or click
- [ ] **Verify in EDGAR** — optional link to original filing in SEC EDGAR

---

## Phase 11: Error Handling & Observability

### Error Paths
- [ ] **401 Unauthorized** — invalid/expired token
- [ ] **403 Forbidden** — user accesses another user's thread
- [ ] **404 Not Found** — missing thread or source document
- [ ] **502 Bad Gateway** — OpenAI or Supabase failure, grounding failure
- [ ] **500 Internal Server Error** — unexpected failure (logged with full context)

### Logging & Monitoring
- [ ] **Structured logs** — use structlog, log user_id, thread_id, retrieval stats, token usage
- [ ] **Error boundaries** — frontend catches and displays friendly messages
- [ ] **Local debugging** — ensure errors are reproducible and logs guide diagnosis

---

## Phase 12: UI Polish & Testing

### Chat Experience
- [ ] **Empty state** — guidance for new conversation, prompt suggestions
- [ ] **Loading states** — show "retrieving documents...", "generating answer..."
- [ ] **Error messages** — friendly user-facing messages + technical detail in logs
- [ ] **Responsive design** — works on desktop (mobile out of scope per brief)

### Manual Testing (Pre-Pilot)
- [ ] **Ask sample questions** — test 3–5 example questions from client brief
- [ ] **Verify citations** — spot-check that citations point to correct passages
- [ ] **Edge cases** — question outside corpus, ambiguous question, multi-document question
- [ ] **Performance** — measure end-to-end latency (question → answer)

---

## Phase 13: Deployment & Handoff

### Railway Setup
- [ ] **Frontend service** — static Vite build served as web app
- [ ] **Backend service** — FastAPI running on Uvicorn, scaled per load
- [ ] **Environment vars** — all secrets injected via Railway secrets UI
- [ ] **Postgres connection** — use session connection (not pooler) for migrations

### Pilot Handoff
- [ ] **User docs** — how to sign in, how to ask questions, how to verify sources
- [ ] **FAQ** — what the bot can/cannot do, why it refuses to give investment advice
- [ ] **Feedback channel** — Slack or email for pilot group to report bugs, request features
- [ ] **Metrics baseline** — measure how much time the 5 analysts save in first week

---

## Definition of Done

✅ Pilot group (5 analysts) uses the app for a week  
✅ Reports ≥3 hours/analyst/week time saved  
✅ No hallucinations detected (every answer cites corpus)  
✅ Rollout ready for the 40-analyst firm
