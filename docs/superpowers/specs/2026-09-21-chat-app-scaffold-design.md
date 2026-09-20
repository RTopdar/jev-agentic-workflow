# Chat App Scaffold — Backend + Frontend Design

Date: 2026-09-21
Status: Approved

## Purpose

Build the plumbing for a multi-agent chat application: FastAPI backend (Postgres via SQLModel), React frontend with SSE streaming. The AI decision layer (langgraph for agent execution, Jev for routing/severity/escalation) is explicitly **out of scope** for this phase and will be planned separately. This scaffold must leave a clean seam for that layer to attach into.

## Non-goals (this phase)

- No langgraph agent graph implementation
- No Jev classifier wiring (routing choice, severity score, escalation decision)
- No auth — single implicit user
- No agent system prompts / instructions storage — only name + description (enough for a future Jev `Choice` to pick among agents)

## Data Model (SQLModel)

**Agent**
- `id: int` (pk)
- `name: str`
- `description: str` — used later as Jev `Choice` criteria text
- `created_at: datetime`

**Conversation**
- `id: int` (pk)
- `status: Literal["active", "escalated", "closed"]` — default `active`
- `created_at: datetime`

**Message**
- `id: int` (pk)
- `conversation_id: int` (fk -> Conversation)
- `role: Literal["user", "agent", "system"]`
- `agent_id: int | None` (fk -> Agent, null when role="user")
- `content: str`
- `severity: float | None` — filled by Jev later; null until AI layer exists
- `escalated: bool` — default False; set True when Jev's escalation question later resolves true
- `created_at: datetime`

Rationale: a full conversation is `Conversation` -> many `Message`. Jev's future routing step reads the last 5 `Message` rows for a conversation plus all `Agent` rows (name/description) to produce two answers: which agent to hand off to, and whether to escalate. `severity`/`escalated` exist now as nullable/default fields so the schema doesn't change shape when that logic lands — only `streaming_service.py` internals change.

## Backend Structure (MVC-style, FastAPI + SQLModel)

```
backend/
  app/
    main.py                 # FastAPI app, mounts routers, DB init on startup
    config.py                # pydantic-settings: DATABASE_URL etc.
    db/
      session.py             # async engine + get_session dependency
    models/                  # SQLModel classes — table AND request/response schema
      agent.py
      conversation.py
      message.py
    controllers/              # thin route handlers, call services, no business logic
      agent_controller.py
      conversation_controller.py
      message_controller.py
    services/                 # business logic lives here — the attach point for future AI layer
      agent_service.py
      conversation_service.py
      message_service.py
      streaming_service.py    # STUB: generates placeholder reply tokens; swap internals later for langgraph+Jev call
    routes/
      __init__.py             # aggregates all routers into one APIRouter
    alembic/                  # migrations
      versions/
```

Each service function is a plain async function taking a DB session + typed args, returning SQLModel instances — so wiring langgraph/Jev later means editing `streaming_service.py` only; controllers/routes/models untouched.

## Endpoints

- `POST /agents` — create agent (name, description) -> Agent
- `GET /agents` — list agents
- `POST /conversations` — create conversation -> Conversation
- `GET /conversations/{id}` — fetch conversation + its messages
- `POST /conversations/{id}/messages` — user sends a message; creates `Message(role="user")`; triggers stub reply generation; returns `{"message_id": <new agent message id>}` (id pre-created in `pending` content state so the client can immediately open a stream against it)
- `GET /messages/{id}/stream` — SSE endpoint; streams the agent reply's tokens for that message id as they're produced by `streaming_service`; on completion, writes final `content`/`severity`/`escalated` to the Message row and closes the stream

## Streaming Flow

1. Client `POST`s user message.
2. Backend persists user `Message`, creates a placeholder agent `Message` row (empty content), returns its id.
3. Client opens `EventSource` against `GET /messages/{id}/stream`.
4. `streaming_service.generate_reply(...)` (stub: yields a few canned tokens with small delays) streams `data: <token>` events.
5. On stream end, backend updates the Message row with full content, and (stub, for now) leaves `severity`/`escalated` null/false.
6. If a future real implementation sets `escalated=True`, it also flips `Conversation.status` to `"escalated"`.

## Frontend Structure (React + Vite)

```
frontend/
  src/
    api/
      client.ts          # base fetch wrapper
      conversations.ts   # createConversation, getConversation
      messages.ts         # sendMessage, streamReply (EventSource wrapper)
    hooks/
      useConversation.ts
      useSSEStream.ts
    components/
      ChatWindow.tsx
      MessageBubble.tsx
      AgentBadge.tsx
      EscalationBanner.tsx
    pages/
      ChatPage.tsx
    App.tsx
```

Single conversation view. `MessageBubble` shows agent name badge when `role="agent"`. `EscalationBanner` renders when `conversation.status === "escalated"`, and the composer disables further input in that state.

## Error Handling

- Standard FastAPI validation errors (422) for malformed requests.
- 404 for unknown conversation/message ids.
- SSE stream sends a final `event: error` frame and closes if `streaming_service` raises, so the frontend can show a retry affordance instead of hanging.

## Testing

- Backend: pytest + httpx `AsyncClient` against an in-memory/test Postgres (or SQLite for unit speed) — CRUD + streaming endpoint smoke tests.
- Frontend: component test for `MessageBubble`/`EscalationBanner` rendering states; skip exhaustive e2e for this phase.

## Open Decisions (deferred to AI-layer phase)

- Exact Jev `Choice`/`Score` wiring in `streaming_service.py`
- How langgraph agent graph maps to `Agent` DB rows
- Whether severity is a `Score` (0-1) or categorical
