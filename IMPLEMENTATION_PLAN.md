# Implementation Plan — jev-agentic-workflow

Narrative architecture and open decisions for this project. Kept in sync with the codebase by the doc-sync flow (AGENTS.md rule #4). Treat drift between this file and the actual code as a bug.

## Status

Alpha — two tracks in the repo:

- **Auto-mode middleware** (root-level `middleware.py`/`orchestrator.py`) — functional, intent-gated multi-step tool execution, full test suite.
- **Chat app scaffold** (`backend/`, `frontend/`) — full FastAPI + SQLModel + Postgres backend and React + Vite + SSE frontend are scaffolded and tested end-to-end, but the AI layer (agent routing, severity/escalation scoring) is a stub. `streaming_service.py` yields canned tokens; the langgraph + Jev integration is not implemented yet.

## Dependencies

- **pydantic** (2.13.5) — data validation and serialization
- **pydantic-settings** (2.15.0) — environment-based config management
- **langchain-typesafe** (0.0.1a3) — LangChain integration with TypeSafe System One models (jev)
- **pytest** (7.4+) / **pytest-asyncio** (0.21+) — test framework
- **fastapi** (0.141+), **uvicorn[standard]** — backend HTTP framework/server (chat app scaffold)
- **sqlmodel** (0.0.42+), **asyncpg**, **alembic** — ORM, async Postgres driver, migrations (chat app scaffold)
- **aiosqlite**, **httpx**, **psycopg2-binary** (dev) — backend test/tooling deps for the chat app scaffold
- Frontend: React + Vite (see `frontend/package.json`); no new architectural dependency beyond the standard Vite toolchain

## Components

### Auto-mode middleware (root)

- **middleware.py** — `AutoModeMiddleware` class using Jev for intent classification (safe/risky/dangerous) and `ToolGate` config for access control
- **orchestrator.py** — `WorkflowOrchestrator` chains intent-gated tools in multi-step workflows; `ToolExecutor` (ungated) and `GatedToolExecutor` (permission-checked)
- **example_usage.py** — runnable scenarios: safe read, safe bash, multi-step workflow, low-confidence blocking
- **test_middleware.py** — pytest suite for middleware intent classification, tool gating, orchestration workflows
- **main.py** — entry point that runs example scenarios

### Chat app scaffold — backend (`backend/app/`)

- **models/** — SQLModel tables: `Agent{id,name,description,created_at}`, `Conversation{id,status,created_at}`, `Message{id,conversation_id,role,agent_id,content,severity,escalated,created_at}`
- **services/** — business logic, one module per resource: `agent_service.py`, `conversation_service.py`, `message_service.py` (CRUD over the models above), plus `streaming_service.py` (see below)
- **streaming_service.py** — **stub seam for the future AI layer.** Currently `generate_reply()` yields a fixed list of canned tokens with a small `asyncio.sleep` between each. This is the explicit attachment point for langgraph + Jev: agent routing via Jev `Choice` (reading `Agent.name`/`description` + last 5 messages) and severity/escalation via Jev `Score`. Not implemented yet.
- **controllers/** — thin FastAPI route handlers per resource (`agent_controller.py`, `conversation_controller.py`, `message_controller.py`); `message_controller.py` also owns the SSE endpoint (`generate_reply` → `data: <token>` events, then `event: done`, finalizing the pending agent `Message` row)
- **routes/__init__.py** — aggregates the three controller routers into a single `api_router`, mounted in `main.py`
- **db/session.py** — async SQLAlchemy engine + `AsyncSession` factory; `init_db()` creates tables from `SQLModel.metadata` at app startup (lifespan hook in `main.py`)
- **config.py** — pydantic-settings `Settings`, reads the single repo-root `.env` via an absolute path (`Path(__file__).resolve().parents[2] / ".env"`) rather than a per-package `.env` (inferred from code: consolidates config to one root `.env` for both `backend/` and any future services)
- **main.py** — FastAPI app factory; CORS middleware allowing `http://localhost:5173` (the Vite dev server); mounts `api_router`
- **alembic/** — migration environment + initial-tables revision (`1dde6dca8bbb_initial_tables.py`)
- **tests/** — endpoint tests per resource, `test_db_session.py`, `test_models.py`, `test_streaming_endpoint.py`, `conftest.py` fixtures

Endpoints exposed: `POST/GET /agents`, `POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/messages`, `GET /conversations/{id}/messages/{message_id}/stream` (SSE).

### Chat app scaffold — frontend (`frontend/src/`)

- **api/** — fetch wrappers (`client.ts`, `conversations.ts`, `messages.ts`) calling the backend REST/SSE endpoints
- **hooks/useSSEStream.ts** — wraps `EventSource`, streams tokens via callback, fires a completion callback on the `done` event
- **components/** — `MessageBubble`, `AgentBadge`, `EscalationBanner`, `ChatWindow` (presentational, one concern each)
- **pages/ChatPage.tsx** — single-conversation page: creates a conversation on mount, sends messages, streams the pending agent reply token-by-token via `useSSEStream`, refreshes conversation state on completion, disables input when conversation status is `"escalated"`
- No auth, no multi-conversation UI (single-conversation scaffold, by design per the linked spec)

## Architecture

**Intent Classification Pipeline (auto-mode middleware):**

1. User request → Jev's `Choice` primitive classifies intent (safe/risky/dangerous) with confidence
2. Tool gate checks intent against allowed modes (e.g., bash only allowed in SAFE mode)
3. Low-confidence (<60%) requests blocked regardless of mode
4. Orchestrator chains multiple gated steps, halting on first blocked step

**Key Design (auto-mode middleware):**

- Jev makes the judgment; code owns control flow (requests denied at the gate, not by model refusal)
- Tool registration separates ungated (read) from gated (bash/delete) operations
- Confidence thresholding prevents ambiguous requests reaching dangerous tools
- Multi-step workflows share user intent context across steps

**Chat app scaffold layering:**

- MVC-ish backend: `routes/` (aggregation) → `controllers/` (thin HTTP handlers, request/response models) → `services/` (business logic, DB access) → `models/` (SQLModel tables). Controllers never touch the DB session directly beyond passing it to a service.
- `streaming_service.py` is intentionally decoupled from the controller's request content (`generate_reply("")` — the stub ignores its input) so swapping in the real langgraph/Jev pipeline later only requires changing this one module's internals, not its call sites.
- Single root `.env` (not per-package) — settings resolve it via an absolute path computed from `config.py`'s own location, so it works regardless of the process's current working directory.
- Frontend treats the backend purely as a REST+SSE API; no shared code/types between `backend/` and `frontend/` (each defines its own message/conversation shape).

## Open Decisions

- Confidence threshold (60%) — tunable per gate or global? *(auto-mode middleware)*
- Escalation path for blocked requests — log only, or route to human review? *(auto-mode middleware)*
- Intent cache — should repeated identical requests reuse classification? *(auto-mode middleware)*
- Agent routing and severity/escalation scoring for chat messages — designed (Jev `Choice` and `Score`) but not implemented; `streaming_service.py` remains a stub until this lands.
- Multi-conversation support / auth for the chat frontend — explicitly out of scope for this scaffold; revisit if the app moves past single-user demo use.
- Langgraph thread/session management — reuse `Conversation.id` directly as langgraph's `thread_id` (no separate UUID field). Postgres (`Message` rows) stays the source of truth for display history; langgraph's checkpointer owns graph-execution state/memory keyed by that same id.

## Changelog

- 2026-09-21: Added auto-mode middleware stack (middleware.py, orchestrator.py, example_usage.py, test_middleware.py); full pytest suite; updated pyproject.toml with dev dependencies.
- 2026-09-21: Scaffolded full-stack chat app (`backend/` FastAPI+SQLModel+Postgres, `frontend/` React+Vite+SSE) on `chat-app-scaffold` branch. Added `Agent`/`Conversation`/`Message` models, per-resource services/controllers/routes, SSE reply streaming via a stub `streaming_service.py` (explicit seam for future langgraph+Jev agent routing/scoring), Alembic migrations, and a single-conversation React chat UI. Consolidated settings on one root `.env`, fixed tz-naive datetime columns, added CORS. Root `pyproject.toml` gained fastapi/uvicorn/sqlmodel/asyncpg/alembic runtime deps and aiosqlite/httpx/psycopg2-binary dev deps. Updated `doc/feature/` with new concept docs for the backend data model, service layer, streaming seam, and frontend chat UI; doc-sync pass performed by the `doc-sync` subagent.
