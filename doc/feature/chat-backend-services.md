---
type: Module
title: Chat App Backend — Routes, Controllers, Services
description: MVC-ish FastAPI layering for the chat app scaffold (backend/app/)
resource: backend/app/routes/, backend/app/controllers/, backend/app/services/, backend/app/db/session.py, backend/app/config.py, backend/app/main.py
tags: [backend, fastapi, sqlmodel, chat-app]
status: alpha
---

## Overview

The chat app backend (`backend/app/`) is layered MVC-style: `routes/` aggregates per-resource `controllers/`, which are thin FastAPI handlers delegating to `services/` for business logic and DB access against the models in [Chat App Data Model](/doc/feature/chat-backend-data-model.md).

## Layers

- **`db/session.py`** — async SQLAlchemy engine (`create_async_engine(settings.database_url)`) and `AsyncSession` factory (`get_session`, a FastAPI dependency); `init_db()` creates tables from `SQLModel.metadata` on startup.
- **`config.py`** — `Settings` (pydantic-settings) with a single field, `database_url`. Reads the repo-root `.env` via an absolute path (`Path(__file__).resolve().parents[2] / ".env"`) instead of a per-package `.env`, so config is consolidated at the repo root regardless of process cwd (inferred from code, commit `b66e2d1`).
- **`services/agent_service.py`** — `create_agent`, `list_agents`.
- **`services/conversation_service.py`** — `create_conversation`, `get_conversation`, `get_messages`, `set_status`.
- **`services/message_service.py`** — `create_user_message`, `create_pending_agent_message` (empty-content placeholder row created immediately so the client has a `message_id` to stream into), `get_message`, `finalize_agent_message`.
- **`controllers/agent_controller.py`, `conversation_controller.py`, `message_controller.py`** — thin route handlers; own request/response Pydantic models; raise `HTTPException(404)` for missing conversations/messages; call straight into the corresponding service.
- **`routes/__init__.py`** — combines the three controller routers into `api_router`, mounted once in `main.py`.
- **`main.py`** — FastAPI app; `lifespan` hook calls `init_db()`; CORS middleware allows `http://localhost:5173` (Vite dev server) with all methods/headers.

## Endpoints

- `POST /agents`, `GET /agents`
- `POST /conversations`
- `GET /conversations/{id}`
- `POST /conversations/{id}/messages`
- `GET /conversations/{id}/messages/{message_id}/stream` (SSE — see [Chat Reply Streaming Seam](/doc/feature/chat-streaming-seam.md))

## Design Notes

- Controllers never touch `AsyncSession` beyond passing it through (`Depends(get_session)`) into a service call — no query logic in `controllers/`.
- `POST /conversations/{id}/messages` creates the user message *and* a pending empty agent message in the same call, returning the pending message's id so the client immediately knows what to open an SSE stream against.
- Migrations live in `backend/alembic/`, independent of the dev-only `init_db()` auto-create path.

## Open Questions

- No auth/authorization on any endpoint (matches the frontend's no-auth, single-conversation scope — explicit scaffold decision, not an oversight).

## Related

- [Chat App Data Model](/doc/feature/chat-backend-data-model.md)
- [Chat Reply Streaming Seam](/doc/feature/chat-streaming-seam.md)
- [Chat Frontend UI](/doc/feature/chat-frontend-ui.md)
