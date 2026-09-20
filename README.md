# jev-agentic-workflow

A multi-agent chat application. A FastAPI + Postgres backend and a React chat UI are scaffolded and working end-to-end; the AI layer that actually picks an agent and generates replies (LangGraph for orchestration, [Jev](https://typesafe.ai) for routing/severity judgments) is the next piece to build.

## Architecture

```
┌─────────────┐        REST + SSE        ┌──────────────┐        SQL        ┌────────────┐
│   frontend   │ ───────────────────────▶ │   backend    │ ─────────────────▶ │  postgres  │
│ React + Vite │ ◀─────────────────────── │   FastAPI    │ ◀───────────────── │            │
└─────────────┘                           └──────┬───────┘                    └────────────┘
                                                  │
                                          streaming_service.py
                                        (stub today — the seam
                                       where LangGraph + Jev plug in)
```

- **Backend** (`backend/app/`) — FastAPI, MVC-ish layering: `routes/` → `controllers/` (thin HTTP handlers) → `services/` (business logic, DB access) → `models/` (SQLModel tables: `Agent`, `Conversation`, `Message`). Async Postgres via SQLModel/asyncpg, migrations via Alembic.
- **Frontend** (`frontend/src/`) — React + Vite, single-conversation chat UI, streams agent replies token-by-token over Server-Sent Events.
- **`streaming_service.py`** is a deliberate stub: it yields canned tokens today. It's the one module that will be swapped for the real pipeline — a LangGraph graph that uses Jev's `Choice` primitive to pick which agent responds (reading each `Agent.name`/`description` plus the conversation's last 5 messages) and Jev's `Score` primitive to judge severity/escalation. `Conversation.id` is reused directly as LangGraph's `thread_id`; Postgres stays the source of truth for message history, LangGraph's checkpointer owns graph-execution state.

See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for the full narrative architecture and open decisions, and [`doc/feature/`](doc/feature/index.md) for one-concept-per-file module docs.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/agents` | Create an agent (`name`, `description`) |
| `GET` | `/agents` | List agents |
| `POST` | `/conversations` | Start a conversation |
| `GET` | `/conversations/{id}` | Fetch a conversation + its messages |
| `POST` | `/conversations/{id}/messages` | Send a user message; creates a pending agent reply |
| `GET` | `/conversations/{id}/messages/{message_id}/stream` | SSE stream of the agent reply's tokens |

## Prerequisites

- Python 3.13+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- A running Postgres instance (this project was developed against a local native install; any reachable Postgres works)

## Setup

1. Install backend dependencies:

   ```bash
   uv sync --extra dev
   ```

2. Install frontend dependencies:

   ```bash
   cd frontend && npm install && cd ..
   ```

3. Create a `.env` at the repo root (see `.env.example`) with at least:

   ```env
   DATABASE_URL=postgresql+asyncpg://youruser@localhost:5432/jev_chat
   ```

   Create the database itself first, e.g. `createdb jev_chat`.

4. Run migrations:

   ```bash
   cd backend && uv run --project .. alembic upgrade head && cd ..
   ```

## Running it

Start Postgres (if it isn't already running as a service), then in two terminals:

```bash
# backend — from backend/
uv run --project .. uvicorn app.main:app --reload --port 8000

# frontend — from frontend/
npm run dev
```

Or, if you're on a GNOME desktop, run the whole stack in one shot:

```bash
./dev.sh
```

This opens three `gnome-terminal` tabs — backend, frontend, and Postgres. If Postgres is already running, that tab just shows cluster status and tails its log; if not, it runs `sudo systemctl start postgresql` (may prompt for your password in that tab) before tailing the log. If `gnome-terminal` isn't available, the script prints the manual commands instead.

Then open `http://localhost:5173`.

## Testing

```bash
# backend
uv run --extra dev pytest backend/tests/ -v

# frontend
cd frontend && npm test
```

## Repo conventions for AI coding agents

This repo ships `AGENTS.md` / `CLAUDE.md` behavioral rules and `.claude/agents/` subagent specs (`incident-handler` for bugs, `doc-sync` for keeping `IMPLEMENTATION_PLAN.md` and `doc/feature/` in sync with code) — see [`AGENTS.md`](AGENTS.md) if you're an agent working in this codebase.

## License

MIT — see [LICENSE](LICENSE).
