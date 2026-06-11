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

## How the rest of this plan is organized

The original plan laid out Phases 2–13 as horizontal layers — build all of auth, then all of the API, then all of the frontend, then all of retrieval, then all of grounding, and so on. That defers anything demoable until very late and means retrieval/grounding work gets built and "finished" before there's a real user-facing loop to validate it against.

The plan below replaces that with **vertical slices** — tracer bullets that each cut through the full stack (DB → backend → frontend) and end in something you can actually demo. **Track A (corpus ingestion)** is the one prerequisite that has to land early, in parallel with the first slices, so that later retrieval and grounding slices have real embedded data to work against rather than empty tables.

Each slice below states its goal, its definition of done as a demoable scenario, and the concrete checklist of things that need to exist — including the error paths and redeploys that belong to that slice, rather than deferring them to a separate hardening or deployment phase at the end.

---

## Slice 1: Chat Plumbing — prove the wiring end to end

**Goal:** Real Supabase login → send a message → stubbed streamed reply → persisted to the database → still there on reload. Every hop is real — no mocked layers — before any LLM or retrieval work begins.

**Definition of done:** Log in with a real Supabase session, land in a single auto-created thread, send a message, watch a hardcoded reply stream token-by-token, refresh the page, and see the conversation intact. An invalid token returns 401; a missing thread returns 404. The app is live on Railway.

### Backend
- [x] **Supabase Auth verification** — `AuthService` validates `Authorization: Bearer <token>` at the FastAPI boundary
- [x] **JWT verification** — call Supabase Auth or validate signing keys locally
- [x] **User creation** — link Supabase `auth.users.id` to `profiles` on first login
- [x] **Route protection** — `@require_auth` dependency on restricted endpoints
- [x] **Chat persistence layer** — `app/database/chats.py` create/read a thread and its messages
- [x] **POST /chat/stream** — accept thread ID + messages, verify user owns thread, stream a response
- [x] **Request/response types** — Pydantic models for message format and streaming events
- [x] **Stub assistant response** — hardcoded "answer not yet implemented" to test streaming plumbing
- [x] **Orchestrator skeleton** — `app/chat/orchestrator.py` and `app/chat/messages.py` coordinate one turn against the stub
- [x] **Error handling** — 401 for invalid/missing token, 404 for missing thread

### Frontend
- [x] **Vite project** — `frontend/` with React + TypeScript
- [x] **Environment config** — `src/lib/env.ts` reads and validates `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [x] **Supabase client** — `src/lib/supabase.ts` initializes the browser Supabase instance
- [x] **HTTP client** — `src/lib/http.ts` wraps fetch, injects the auth token, handles errors
- [x] **Routing** — React Router with `/` (home), `/chat/:threadId`, `/login`
- [x] **Supabase Auth UI** — sign in with Driftwood email, session storage, logout
- [x] **Route guards** — redirect unauthenticated users to `/login`
- [x] **Install Vercel AI SDK** — `@vercel/ai` for chat components and the streaming client
- [x] **useChat hook** — initialize with thread ID and message history, transport = `/chat/stream`
- [x] **Message display** — render user and assistant messages, show loading state
- [x] **Send message** — capture input, post to backend, stream the response into the UI
- [x] **Error boundary** — catch and display a friendly message on request failure

### Deploy
- [x] **Railway services** — stand up the frontend (static Vite build) and backend (FastAPI/Uvicorn) services
- [x] **Environment vars** — inject all secrets via the Railway secrets UI
- [x] **Postgres connection** — use the session connection (not the pooler) for migrations
- [x] **Confirm live** — log in and send a message against the deployed app

---

## Track A: Corpus Ingestion — prerequisite, run once in parallel with Slices 1–2

**Goal:** Get the full sample corpus parsed, chunked, embedded, and stored before any retrieval-touching slice needs real data. This isn't a user-facing slice — nobody demos ingestion — but Slice 3 only proves anything if it's grounded in real, embedded chunks rather than empty tables.

**Definition of done:** All 5 companies × ~5 filings (2021–2025) are downloaded, parsed, chunked, embedded, and loaded — verified by spot-checking chunk counts and a sample of embeddings against source text.

- [x] **Download SEC filings** — use `data/download.py` to fetch 10-Ks from EDGAR (Netflix, Tesla, Costco, JPMorgan, United Healthcare, 2021–2025)
- [x] **Parse to Markdown** — convert HTML/XML filings to normalized Markdown, extract metadata (ticker, CIK, filing date, accession number)
- [x] **Document persistence layer** — `app/database/documents.py` for storing source docs, chunks, embeddings
- [x] **Store source documents** — persist normalized Markdown in `source_documents`
- [x] **Chunking logic** — split documents into semantic chunks (~500 tokens), preserve metadata (page/section, original offset)
- [x] **OpenAI embeddings** — call the embedding API per chunk, store 1536-dim vectors in `document_chunks.embedding`
- [x] **Full-text search vectors** — generate `tsvector` for lexical search in `document_chunks.search_vector`
- [x] **Batch ingestion** — load all chunks and vectors into Supabase in one batch
- [x] **Spot-check** — 7,948 chunks ingested across 25 filings (5 companies × 5 years)

---

## Slice 2: Thread Management — fast follow

**Goal:** Give analysts a ChatGPT/Claude-style conversation experience — persistent sidebar, multi-thread history, and a blank composer on home that creates a thread implicitly on first send.

**Definition of done:** Land on home, see a blank composer and past threads in a sidebar. Send a first message — URL changes to `/chat/:threadId`, thread appears in sidebar with a truncated title. Click a past thread — correct isolated history loads. Switch threads freely. A missing or non-existent thread returns 404. Redeployed and confirmed live.

### Backend
- [x] **`list_threads`** — add to `app/database/chats.py`; select id, title, updated_at ordered by `updated_at DESC`
- [x] **`create_thread`** — add to `app/database/chats.py`; insert row, return new thread
- [x] **`set_thread_title`** — add to `app/database/chats.py`; update title to first 60 chars of first user message, trimmed at word boundary
- [x] **Remove `get_or_create_thread`** — no longer needed; delete from `app/database/chats.py`
- [x] **`GET /threads`** — returns `list[ThreadSummary]` (id, title, updated_at)
- [x] **`POST /threads`** — creates thread, returns `ThreadSummary`
- [x] **`GET /threads/{thread_id}`** — returns `ThreadDetail` (id, title, messages); replaces old `GET /thread`
- [x] **Delete `GET /thread`** — Slice 1 crutch; confirm no frontend calls remain
- [x] **Auto-title on first message** — in `POST /chat/stream`, after persisting the user message, if thread had no prior messages call `set_thread_title`
- [x] **Error handling** — 404 for missing or unauthorized thread (RLS collapses both cases; no 403 needed)

### Frontend
- [x] **`AppShell` layout component** — sidebar (fixed left) + main content area; wraps all protected routes via layout route in `App.tsx`
- [x] **`Sidebar` component** — calls `GET /threads` on mount; renders thread list with title (fallback: "New conversation") and relative timestamp; highlights active thread; "New chat" button navigates to `/`
- [x] **`HomePage` rewrite** — blank composer (textarea + send); on submit: `POST /threads` → navigate to `/chat/:threadId` with `{ state: { pendingMessage } }`
- [x] **`ChatPage` update** — call `GET /threads/{thread_id}` instead of `GET /thread`; on mount check `location.state.pendingMessage`, auto-submit via `useChat`, clear state
- [x] **`lib/api.ts`** — add typed `getThreads()`, `createThread()`, `getThread(id)` methods
- [x] **Error handling** — 404 on ChatPage shows error state; sidebar load failure is silent (doesn't block chat)

### Deploy
- [x] **Redeploy** — smoke test new user flow (blank composer → send → URL changes → sidebar updates), thread switching, and confirm old `/thread` endpoint is gone

---

## Slice 3: Grounded Answers with Validated Citations — the trust slice

**Goal:** The first slice where a real LLM produces a real answer — and that answer can never reach the user without passing a grounding check first. There must never be a demoable state where an unvalidated citation can appear.

**Definition of done:** Ask one of the brief's simpler single-fact questions (e.g., "What did Netflix's 2023 10-K say about content costs?") and get a real, validated, cited answer; click a citation and see the actual source passage with company/ticker/filing date/page. Ask something outside the corpus and get an honest refusal, never a guess. If the LLM or grounding step fails, the user sees a 502 and no half-message is persisted.

### Schema & config
- [x] **Migration: `match_document_chunks` RPC** — Postgres function for cosine-distance kNN over `document_chunks.embedding` with optional `ticker`/`year` filters on `chunk_metadata`
- [ ] **Migration: `message_citations.marker`** — add a `marker: int` column to preserve `[1]`/`[2]` ordering across reloads
- [ ] **Config** — add `openai_chat_model = "gpt-4o-mini"` to `app/config.py`

### Retrieval (naive — semantic, with metadata filters)
- [x] **Embed user query** — call the OpenAI embedding API on the user's question
- [x] **`app/retrieval/retriever.py`** — calls `match_document_chunks` via the Supabase client; returns full chunk content + metadata; `top_k=8`; optional `ticker`/`year` filters

### Agent (PydanticAI)
- [ ] **Agent module** — `app/assistant/agent.py`: `gpt-4o-mini`, `request_limit=5` per turn
- [ ] **Dependencies** — `app/assistant/deps.py` bundles the Supabase client, retriever, `user_id`, `thread_id`, and a registry of chunk IDs retrieved this run
- [ ] **Output types** — `app/assistant/outputs.py`: `Citation { marker, chunk_id }` (model-produced, minimal), `GroundedAnswer { answer, citations, has_sufficient_evidence }`, `SourcePassage` (backend-hydrated only, never model output)
- [ ] **System instructions** — `app/assistant/instructions.md` encodes the grounding contract: cite every claim from retrieved chunks only; set `has_sufficient_evidence=False` with empty `citations` when the corpus doesn't support an answer; no investment advice
- [ ] **search_filings tool** — `(query, ticker=None, year=None, top_k=8)`; returns full chunk content + metadata; records returned chunk IDs in the deps registry
- [ ] **read_chunk tool** — re-fetches full content by chunk ID; only succeeds for chunk IDs already in the deps registry
- [ ] **Tool constraints** — the agent can only cite chunks recorded in the deps registry for this run

### Grounding & citation validation
- [ ] **Grounding module** — `app/grounding/validator.py`: pure `validate_citations(answer, retrieved_chunk_ids)` checks marker↔citation 1:1 consistency, every `chunk_id` is in the retrieved set, and `has_sufficient_evidence` is consistent with `citations` (non-empty+valid iff `True`)
- [ ] **Self-correction** — wire `validate_citations` as `@agent.output_validator`; on failure raise `ModelRetry` describing the valid markers/chunk IDs, consuming part of the `request_limit` budget
- [ ] **Hard gate** — orchestrator re-runs `validate_citations` after the agent finishes; on failure raise `HTTPException(502)` and persist nothing
- [ ] **Source passage hydration** — build `SourcePassage` objects from the retrieved `document_chunks` rows (content + ticker/company/filing type/date/section), never from model output
- [ ] **Citation persistence** — store `message_citations` records with `marker`, `chunk_id`, and `excerpt` (full chunk content)
- [ ] **Unit tests** — validator pass/fail/refusal/marker-mismatch cases; agent tests via PydanticAI `TestModel`/`FunctionModel` for adversarial outputs (unretrieved chunk_id, mismatched markers, inconsistent `has_sufficient_evidence`)
- [ ] **Integration tests** — full turn: retrieval → agent → validation → persistence, against brief questions #3, #4, #5, #10 plus an out-of-corpus refusal

### Full turn orchestration (validate-then-replay)
- [ ] **Orchestrate one turn** — persist user message → run retrieval+agent+validation fully *before* opening the SSE stream → on success, stream `answer` text as deltas → emit `CitationsEvent` → persist assistant message + citations
- [ ] **502 on failure** — any pipeline failure (retrieval, agent, exhausted retries, validation) raises `HTTPException(502)` before the stream opens; nothing beyond the user message is persisted
- [ ] **Stateless per turn** — agent operates on the current question only; no thread history passed as `message_history` (deferred to a future slice)

### Frontend (basic citation UI)
- [ ] **Streaming contract** — new `CitationsEvent` encoded as `{"type": "data-citations", "data": {"passages": [...]}}`, emitted after `text-end`
- [ ] **Citation display** — `ChatMessage` renders `[1]`/`[2]` markers in the answer text as clickable spans
- [ ] **Source passage viewer** — shadcn `Dialog` modal showing passage content, ticker, company, filing type/date, section
- [ ] **Reload hydration** — `to_ui_message` / `GET /threads/{thread_id}` joins `message_citations` + `document_chunks` to rebuild the same `data-citations` part on history load

### Acceptance
- [ ] **Validate against the brief** — run questions #3, #4, #5, #10 (single-document, single-fact) and confirm cited, grounded answers
- [ ] **Validate refusal** — ask an out-of-corpus question and confirm an honest refusal with no citations
- [ ] **Validate failure path** — confirm a simulated pipeline failure returns 502 with nothing persisted
- [ ] **Redeploy**

---

## Slice 4: Retrieval Quality — hybrid search + RRF

**Goal:** Handle the brief's harder questions — multi-document, multi-year, comparative — that naive semantic-only retrieval will struggle to answer well.

**Definition of done:** Ask a comparative question (e.g., #1 — Netflix's revenue mix shift 2021–2025, or #8 — capex/buybacks across four companies) and get a well-grounded answer that correctly synthesizes across many chunks and years, citing all of them.

- [ ] **Hybrid search** — run Postgres full-text search on `document_chunks.search_vector` alongside semantic search
- [ ] **Reciprocal Rank Fusion** — fuse semantic + lexical ranked lists into one ranked result set
- [ ] **read_surrounding tool** — fetch neighboring chunks for richer grounding context
- [ ] **Retrieval tests** — unit tests verify RRF fusion, surrounding-chunk fetching, and metadata preservation
- [ ] **Validate against the brief** — run questions #1, #2, #6, #7, #8, #9 (multi-document/comparative) and confirm synthesis quality
- [ ] **Redeploy**

---

## Slice 5: Citation UI Polish & Source Verification

**Goal:** Take citations from "functional" to "what an analyst actually trusts and uses to verify a claim in one click."

**Definition of done:** Hover a citation for a quick preview, click it for a polished modal with the full passage and metadata, and follow an optional link to the original filing in SEC EDGAR.

- [ ] **Hover preview** — show a quick passage preview on hover
- [ ] **Source passage modal** — polished modal with full passage, company/ticker/filing date/page
- [ ] **Verify in EDGAR** — link to the original filing in SEC EDGAR

---

## Slice 6: UX Polish & Pre-Pilot Acceptance

**Goal:** Make the app feel like a real product, and confirm — before handing it to analysts — that it's ready for a week of unsupervised use.

**Definition of done:** Empty states, loading states, friendly errors, and a responsive desktop layout are in place, and a final pass re-runs all 10 of the brief's sample questions together as confirmation (not first contact), checks edge cases, and measures latency.

### Chat experience
- [ ] **Empty state** — guidance for a new conversation, prompt suggestions
- [ ] **Loading states** — "retrieving documents...", "generating answer..."
- [ ] **Error messages** — friendly user-facing copy + technical detail in logs
- [ ] **Responsive design** — works well on desktop (mobile out of scope per brief)

### Observability
- [ ] **Structured logging pass** — consistent `structlog` use across slices: user_id, thread_id, retrieval stats, token usage

### Final acceptance
- [ ] **Run all 10 sample questions** — confirm the full set from the client brief works end to end
- [ ] **Verify citations** — spot-check that citations point to correct passages
- [ ] **Edge cases** — question outside the corpus, ambiguous question, multi-document question
- [ ] **Performance** — measure end-to-end latency (question → answer)
- [ ] **Redeploy**

---

## Slice 7: Pilot Handoff

**Goal:** Get the app and the people using it ready for the week-long pilot with 5 senior analysts.

**Definition of done:** A pilot analyst can read the docs, sign in, ask a question, verify a source, knows where to send feedback — and there's a baseline to measure the ≥3 hrs/analyst/week claim against.

- [ ] **User docs** — how to sign in, how to ask questions, how to verify sources
- [ ] **FAQ** — what the bot can/cannot do, why it refuses to give investment advice
- [ ] **Feedback channel** — Slack or email for the pilot group to report bugs, request features
- [ ] **Metrics baseline** — measure how much time the 5 analysts save in week one

---

## Definition of Done

✅ Pilot group (5 analysts) uses the app for a week  
✅ Reports ≥3 hours/analyst/week time saved  
✅ No hallucinations detected (every answer cites the corpus)  
✅ Rollout ready for the 40-analyst firm
