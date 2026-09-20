# Chat App Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working FastAPI + Postgres (SQLModel) backend and React + SSE frontend for a multi-agent chat app, with a clean seam (`streaming_service.py`) where the future langgraph+Jev AI layer attaches.

**Architecture:** MVC-style FastAPI backend — routes → controllers (thin) → services (business logic) → SQLModel models (double as DB tables + schemas). React frontend hits REST endpoints for CRUD and opens an `EventSource` against a per-message SSE endpoint for streaming replies. A stub `streaming_service.generate_reply` yields canned tokens until the AI layer is built later.

**Tech Stack:** Python 3.13, FastAPI, SQLModel, asyncpg, Alembic, pytest + httpx `AsyncClient`, Postgres. React (Vite, TypeScript), native `EventSource`.

**Spec:** `docs/superpowers/specs/2026-09-21-chat-app-scaffold-design.md`

## Global Constraints

- No auth — single implicit user (per spec).
- No agent system-prompt storage — `Agent` has only `name` + `description` (per spec).
- `Message.severity` and `Message.escalated` exist now as nullable/default fields; no Jev/langgraph logic implemented this phase (per spec Non-goals).
- File size cap 500 lines per file (AGENTS.md rule #5) — split further if a file would exceed this.
- Backend files under `backend/app/`; frontend files under `frontend/src/` (per spec structure).
- After this plan's tasks are complete, run `doc-sync` subagent to update `IMPLEMENTATION_PLAN.md` / `AGENTS.md` / `doc/feature/` (CLAUDE.md rule #4) — not part of the tasks below, done once at the end.

---

## Task 1: Backend project setup + DB session

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/session.py`
- Create: `backend/pyproject.toml` (or extend root `pyproject.toml` — see step 1)
- Create: `backend/.env.example`
- Test: `backend/tests/test_db_session.py`

**Interfaces:**
- Produces: `Settings` (pydantic-settings, field `database_url: str`) in `config.py`, importable as `from app.config import settings`
- Produces: `get_session()` async generator dependency in `db/session.py`, `engine` (async SQLModel/SQLAlchemy engine) importable as `from app.db.session import engine, get_session, init_db`
- Produces: `init_db()` async function that creates tables (for test/dev use; Alembic used for real migrations in Task 2)

- [ ] **Step 1: Decide dependency location and add backend deps**

Add to the root `pyproject.toml` `dependencies` list (this repo is single-package, backend lives under `backend/` but imports as `app.*` with `backend` added to path via running uvicorn from that dir):

```toml
dependencies = [
    "black>=26.5.1",
    "langchain-openrouter>=0.2.8",
    "langchain-typesafe[experimental]>=0.0.1a3",
    "pydantic>=2.13.5",
    "pydantic-settings>=2.15.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlmodel>=0.0.22",
    "asyncpg>=0.30",
    "alembic>=1.14",
]
```

Run: `uv sync`
Expected: lockfile updates, no errors.

- [ ] **Step 2: Write `backend/app/__init__.py` and `backend/app/db/__init__.py`**

Both empty files (package markers).

- [ ] **Step 3: Write `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jev_chat"


settings = Settings()
```

- [ ] **Step 4: Write `backend/.env.example`**

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/jev_chat
```

- [ ] **Step 5: Write `backend/app/db/session.py`**

```python
from collections.abc import AsyncGenerator

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
```

- [ ] **Step 6: Write failing test for DB session against SQLite (fast, no Postgres needed for this unit test)**

```python
import pytest
from sqlmodel import SQLModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine


class _Dummy(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


@pytest.mark.asyncio
async def test_session_can_write_and_read():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        session.add(_Dummy(name="hello"))
        await session.commit()

    async with AsyncSession(engine) as session:
        from sqlmodel import select

        result = await session.exec(select(_Dummy))
        rows = result.all()
        assert len(rows) == 1
        assert rows[0].name == "hello"
```

Add `aiosqlite` to dev dependencies (`pyproject.toml` `[project.optional-dependencies].dev`) since this test needs it: `"aiosqlite>=0.20"`.

Run: `uv sync && uv run pytest backend/tests/test_db_session.py -v`
Expected: FAIL (backend/tests doesn't exist yet / import path issue) — create `backend/tests/__init__.py` and a `backend/pytest.ini` or root `pyproject.toml` `[tool.pytest.ini_options]` with `pythonpath = ["backend"]` and `asyncio_mode = "auto"` first, then re-run and confirm it fails only due to missing fixtures if any, not import errors. Since this test is self-contained (no app import), it should actually PASS once dependencies are installed and pytest can find it — treat "installing deps" as the thing you're verifying here.

- [ ] **Step 7: Confirm test passes**

Run: `uv run pytest backend/tests/test_db_session.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock backend/
git commit -m "feat: add backend scaffold with async DB session"
```

---

## Task 2: SQLModel models (Agent, Conversation, Message) + Alembic migration

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/agent.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/message.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `engine`, `get_session`, `init_db` from Task 1 (`app.db.session`)
- Produces: `Agent(SQLModel, table=True)` with `id, name, description, created_at`
- Produces: `Conversation(SQLModel, table=True)` with `id, status, created_at`; `status` is `str` constrained to `"active" | "escalated" | "closed"` via a plain `str` field validated at the service layer (SQLModel/SQLite/Postgres portability — avoid native enum type)
- Produces: `Message(SQLModel, table=True)` with `id, conversation_id, role, agent_id, content, severity, escalated, created_at`

- [ ] **Step 1: Write failing test asserting model shapes**

```python
from datetime import datetime

from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message


def test_agent_fields():
    a = Agent(name="Billing Bot", description="Handles billing questions")
    assert a.name == "Billing Bot"
    assert a.description == "Handles billing questions"
    assert a.id is None


def test_conversation_defaults_to_active():
    c = Conversation()
    assert c.status == "active"


def test_message_fields_and_defaults():
    m = Message(conversation_id=1, role="user", content="hi")
    assert m.agent_id is None
    assert m.severity is None
    assert m.escalated is False
    assert isinstance(m.created_at, datetime)
```

Run: `uv run pytest backend/tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 2: Write `backend/app/models/__init__.py`**

```python
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message

__all__ = ["Agent", "Conversation", "Message"]
```

- [ ] **Step 3: Write `backend/app/models/agent.py`**

```python
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Agent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

- [ ] **Step 4: Write `backend/app/models/conversation.py`**

```python
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

- [ ] **Step 5: Write `backend/app/models/message.py`**

```python
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id")
    role: str
    agent_id: int | None = Field(default=None, foreign_key="agent.id")
    content: str
    severity: float | None = Field(default=None)
    escalated: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_models.py -v`
Expected: PASS

- [ ] **Step 7: Set up Alembic for Postgres migrations**

Run: `cd backend && uv run alembic init alembic`

Edit `backend/alembic/env.py` — replace the `target_metadata = None` line and add imports so autogenerate sees the models:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import SQLModel
from app.models import Agent, Conversation, Message  # noqa: F401
from app.config import settings

target_metadata = SQLModel.metadata
```

Also set `sqlalchemy.url` in `backend/alembic.ini` to read from env, or set it programmatically in `env.py`:

```python
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))
```

(Alembic's default sync engine needs the non-async driver string; psycopg2 or psycopg must be installed for actual migration runs against real Postgres — add `psycopg2-binary` to dev deps if running migrations locally.)

- [ ] **Step 8: Generate initial migration**

Run: `cd backend && uv run alembic revision --autogenerate -m "initial tables"`
Expected: creates `backend/alembic/versions/<hash>_initial_tables.py` with `create_table` calls for agent, conversation, message. Rename this file's slug to match `0001_initial.py` convention if desired, or leave the autogenerated name — either is fine as long as it's the one committed.

- [ ] **Step 9: Commit**

```bash
git add backend/app/models backend/alembic backend/alembic.ini backend/tests/test_models.py
git commit -m "feat: add Agent/Conversation/Message SQLModel models + initial migration"
```

---

## Task 3: Agent service + controller + routes (CRUD)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/agent_service.py`
- Create: `backend/app/controllers/__init__.py`
- Create: `backend/app/controllers/agent_controller.py`
- Create: `backend/app/routes/__init__.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_agent_endpoints.py`

**Interfaces:**
- Consumes: `Agent` model (Task 2), `get_session` (Task 1)
- Produces: `agent_service.create_agent(session, name, description) -> Agent`
- Produces: `agent_service.list_agents(session) -> list[Agent]`
- Produces: `agent_router: APIRouter` (in `agent_controller.py`) mounted at `/agents`
- Produces: `app` FastAPI instance in `main.py`, importable as `from app.main import app`

- [ ] **Step 1: Write failing test for the endpoints**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_and_list_agents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/agents", json={"name": "Billing Bot", "description": "Handles billing"}
        )
        assert resp.status_code == 201
        created = resp.json()
        assert created["name"] == "Billing Bot"
        assert "id" in created

        resp = await client.get("/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert any(a["id"] == created["id"] for a in agents)
```

This test needs a clean DB per run — add a `conftest.py`:

```python
# backend/tests/conftest.py
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.db import session as db_session


@pytest_asyncio.fixture(autouse=True)
async def _test_engine():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    db_session.engine = test_engine
    yield
    await test_engine.dispose()
```

Run: `uv run pytest backend/tests/test_agent_endpoints.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 2: Write `backend/app/services/__init__.py` and `backend/app/controllers/__init__.py` and `backend/app/routes/__init__.py`**

Empty package markers for the first two. `routes/__init__.py` will aggregate — leave as empty for now, filled in Step 5.

- [ ] **Step 3: Write `backend/app/services/agent_service.py`**

```python
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent import Agent


async def create_agent(session: AsyncSession, name: str, description: str) -> Agent:
    agent = Agent(name=name, description=description)
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def list_agents(session: AsyncSession) -> list[Agent]:
    result = await session.exec(select(Agent))
    return list(result.all())
```

- [ ] **Step 4: Write `backend/app/controllers/agent_controller.py`**

```python
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.models.agent import Agent
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreate(Agent):
    id: int | None = None


@router.post("", response_model=Agent, status_code=201)
async def create_agent(
    payload: AgentCreate, session: AsyncSession = Depends(get_session)
) -> Agent:
    return await agent_service.create_agent(session, payload.name, payload.description)


@router.get("", response_model=list[Agent])
async def list_agents(session: AsyncSession = Depends(get_session)) -> list[Agent]:
    return await agent_service.list_agents(session)
```

- [ ] **Step 5: Write `backend/app/routes/__init__.py`**

```python
from fastapi import APIRouter

from app.controllers.agent_controller import router as agent_router

api_router = APIRouter()
api_router.include_router(agent_router)
```

- [ ] **Step 6: Write `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import init_db
from app.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Jev Agentic Chat", lifespan=lifespan)
app.include_router(api_router)
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_agent_endpoints.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/services backend/app/controllers backend/app/routes backend/app/main.py backend/tests/test_agent_endpoints.py backend/tests/conftest.py
git commit -m "feat: add agent CRUD service/controller/routes"
```

---

## Task 4: Conversation + Message services, controllers, routes (create conversation, post message)

**Files:**
- Create: `backend/app/services/conversation_service.py`
- Create: `backend/app/services/message_service.py`
- Create: `backend/app/controllers/conversation_controller.py`
- Create: `backend/app/controllers/message_controller.py`
- Modify: `backend/app/routes/__init__.py`
- Test: `backend/tests/test_conversation_endpoints.py`
- Test: `backend/tests/test_message_endpoints.py`

**Interfaces:**
- Consumes: `Conversation`, `Message` models (Task 2); `get_session` (Task 1)
- Produces: `conversation_service.create_conversation(session) -> Conversation`
- Produces: `conversation_service.get_conversation(session, id) -> Conversation | None`
- Produces: `conversation_service.get_messages(session, conversation_id) -> list[Message]`
- Produces: `message_service.create_user_message(session, conversation_id, content) -> Message` (the user's message)
- Produces: `message_service.create_pending_agent_message(session, conversation_id) -> Message` (empty-content placeholder, `role="agent"`, returned so its `id` can be streamed against)
- Produces: `conversation_router`, `message_router` mounted at `/conversations`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_conversation_endpoints.py
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_and_get_conversation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/conversations")
        assert resp.status_code == 201
        conv = resp.json()
        assert conv["status"] == "active"

        resp = await client.get(f"/conversations/{conv['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == conv["id"]
        assert body["messages"] == []
```

```python
# backend/tests/test_message_endpoints.py
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_post_message_creates_user_and_pending_agent_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        conv_resp = await client.post("/conversations")
        conv_id = conv_resp.json()["id"]

        resp = await client.post(
            f"/conversations/{conv_id}/messages", json={"content": "hello"}
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "message_id" in body

        conv = await client.get(f"/conversations/{conv_id}")
        messages = conv.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hello"
        assert messages[1]["role"] == "agent"
        assert messages[1]["id"] == body["message_id"]
```

Run: `uv run pytest backend/tests/test_conversation_endpoints.py backend/tests/test_message_endpoints.py -v`
Expected: FAIL — 404s, `/conversations` route doesn't exist yet.

- [ ] **Step 2: Write `backend/app/services/conversation_service.py`**

```python
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


async def create_conversation(session: AsyncSession) -> Conversation:
    conversation = Conversation()
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def get_conversation(
    session: AsyncSession, conversation_id: int
) -> Conversation | None:
    return await session.get(Conversation, conversation_id)


async def get_messages(session: AsyncSession, conversation_id: int) -> list[Message]:
    result = await session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    return list(result.all())


async def set_status(
    session: AsyncSession, conversation: Conversation, status: str
) -> Conversation:
    conversation.status = status
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation
```

- [ ] **Step 3: Write `backend/app/services/message_service.py`**

```python
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.message import Message


async def create_user_message(
    session: AsyncSession, conversation_id: int, content: str
) -> Message:
    message = Message(conversation_id=conversation_id, role="user", content=content)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def create_pending_agent_message(
    session: AsyncSession, conversation_id: int
) -> Message:
    message = Message(conversation_id=conversation_id, role="agent", content="")
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def get_message(session: AsyncSession, message_id: int) -> Message | None:
    return await session.get(Message, message_id)


async def finalize_agent_message(
    session: AsyncSession, message: Message, content: str
) -> Message:
    message.content = content
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message
```

- [ ] **Step 4: Write `backend/app/controllers/conversation_controller.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.models.conversation import Conversation
from app.models.message import Message
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationDetail(BaseModel):
    id: int
    status: str
    messages: list[Message]


@router.post("", response_model=Conversation, status_code=201)
async def create_conversation(
    session: AsyncSession = Depends(get_session),
) -> Conversation:
    return await conversation_service.create_conversation(session)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int, session: AsyncSession = Depends(get_session)
) -> ConversationDetail:
    conversation = await conversation_service.get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await conversation_service.get_messages(session, conversation_id)
    return ConversationDetail(
        id=conversation.id, status=conversation.status, messages=messages
    )
```

- [ ] **Step 5: Write `backend/app/controllers/message_controller.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.services import conversation_service, message_service

router = APIRouter(prefix="/conversations", tags=["messages"])


class MessageCreate(BaseModel):
    content: str


class MessageCreateResponse(BaseModel):
    message_id: int


@router.post(
    "/{conversation_id}/messages", response_model=MessageCreateResponse, status_code=201
)
async def post_message(
    conversation_id: int,
    payload: MessageCreate,
    session: AsyncSession = Depends(get_session),
) -> MessageCreateResponse:
    conversation = await conversation_service.get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await message_service.create_user_message(session, conversation_id, payload.content)
    pending = await message_service.create_pending_agent_message(
        session, conversation_id
    )
    return MessageCreateResponse(message_id=pending.id)
```

- [ ] **Step 6: Update `backend/app/routes/__init__.py`**

```python
from fastapi import APIRouter

from app.controllers.agent_controller import router as agent_router
from app.controllers.conversation_controller import router as conversation_router
from app.controllers.message_controller import router as message_router

api_router = APIRouter()
api_router.include_router(agent_router)
api_router.include_router(conversation_router)
api_router.include_router(message_router)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest backend/tests/test_conversation_endpoints.py backend/tests/test_message_endpoints.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/services backend/app/controllers backend/app/routes backend/tests
git commit -m "feat: add conversation/message services, controllers, routes"
```

---

## Task 5: Streaming service (stub) + SSE endpoint

**Files:**
- Create: `backend/app/services/streaming_service.py`
- Modify: `backend/app/controllers/message_controller.py`
- Modify: `backend/app/routes/__init__.py` (no change expected — same router, new route in same controller)
- Test: `backend/tests/test_streaming_endpoint.py`

**Interfaces:**
- Consumes: `message_service.get_message`, `message_service.finalize_agent_message` (Task 4)
- Produces: `streaming_service.generate_reply(user_content: str) -> AsyncIterator[str]` — stub yielding fixed tokens with a short `asyncio.sleep` between them
- Produces: `GET /messages/{message_id}/stream` SSE route returning `text/event-stream`

- [ ] **Step 1: Write failing test**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_stream_reply_emits_tokens_and_finalizes_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        conv_resp = await client.post("/conversations")
        conv_id = conv_resp.json()["id"]
        msg_resp = await client.post(
            f"/conversations/{conv_id}/messages", json={"content": "hello"}
        )
        message_id = msg_resp.json()["message_id"]

        async with client.stream("GET", f"/messages/{message_id}/stream") as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            body = ""
            async for chunk in resp.aiter_text():
                body += chunk
            assert "data:" in body

        conv = await client.get(f"/conversations/{conv_id}")
        agent_message = conv.json()["messages"][1]
        assert agent_message["content"] != ""
```

Run: `uv run pytest backend/tests/test_streaming_endpoint.py -v`
Expected: FAIL with 404 (route doesn't exist)

- [ ] **Step 2: Write `backend/app/services/streaming_service.py`**

```python
import asyncio
from collections.abc import AsyncIterator

_STUB_TOKENS = ["Thanks ", "for ", "your ", "message. ", "This ", "is ", "a ", "stub ", "reply."]


async def generate_reply(user_content: str) -> AsyncIterator[str]:
    for token in _STUB_TOKENS:
        await asyncio.sleep(0.01)
        yield token
```

- [ ] **Step 3: Add SSE route to `backend/app/controllers/message_controller.py`**

Add these imports and route to the existing file:

```python
from fastapi.responses import StreamingResponse

from app.services import message_service, streaming_service
```

```python
@router.get("/{conversation_id}/messages/{message_id}/stream")
async def stream_message_reply(
    conversation_id: int,
    message_id: int,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    message = await message_service.get_message(session, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    async def event_stream():
        full_content = ""
        async for token in streaming_service.generate_reply(""):
            full_content += token
            yield f"data: {token}\n\n"
        await message_service.finalize_agent_message(session, message, full_content)
        yield "event: done\ndata: end\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

Note: route path is `/conversations/{conversation_id}/messages/{message_id}/stream` (nested under the existing `/conversations` prefix on this router) rather than the flatter `/messages/{id}/stream` in the spec — adjust the test above and the frontend task to match this actual path, since `message_controller`'s router prefix is `/conversations`. Use `/conversations/{conversation_id}/messages/{message_id}/stream` consistently.

Update the test in Step 1 to call `client.stream("GET", f"/conversations/{conv_id}/messages/{message_id}/stream")`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_streaming_endpoint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/streaming_service.py backend/app/controllers/message_controller.py backend/tests/test_streaming_endpoint.py
git commit -m "feat: add stub streaming service and SSE reply endpoint"
```

---

## Task 6: Frontend scaffold — API client + hooks

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/conversations.ts`
- Create: `frontend/src/api/messages.ts`
- Create: `frontend/src/hooks/useSSEStream.ts`
- Test: `frontend/src/api/messages.test.ts`

**Interfaces:**
- Consumes: backend endpoints from Tasks 3-5 (`POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/messages`, `GET /conversations/{id}/messages/{message_id}/stream`)
- Produces: `createConversation(): Promise<Conversation>`, `getConversation(id): Promise<ConversationDetail>` in `api/conversations.ts`
- Produces: `sendMessage(conversationId, content): Promise<{message_id: number}>` in `api/messages.ts`
- Produces: `useSSEStream(url: string, onToken: (t: string) => void, onDone: () => void): void` hook in `hooks/useSSEStream.ts`

- [ ] **Step 1: Scaffold Vite project**

Run: `cd frontend 2>/dev/null || (mkdir frontend && cd frontend); npm create vite@latest . -- --template react-ts`
Expected: Vite project files created (package.json, vite.config.ts, tsconfig.json, index.html, src/main.tsx, src/App.tsx).

Run: `cd frontend && npm install && npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`

- [ ] **Step 2: Write `frontend/src/api/client.ts`**

```typescript
const BASE_URL = "http://localhost:8000";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    throw new Error(`Request failed: ${resp.status}`);
  }
  return resp.json() as Promise<T>;
}

export { BASE_URL };
```

- [ ] **Step 3: Write `frontend/src/api/conversations.ts`**

```typescript
import { apiFetch } from "./client";

export interface Message {
  id: number;
  conversation_id: number;
  role: "user" | "agent" | "system";
  agent_id: number | null;
  content: string;
  severity: number | null;
  escalated: boolean;
  created_at: string;
}

export interface Conversation {
  id: number;
  status: "active" | "escalated" | "closed";
  created_at: string;
}

export interface ConversationDetail {
  id: number;
  status: string;
  messages: Message[];
}

export function createConversation(): Promise<Conversation> {
  return apiFetch<Conversation>("/conversations", { method: "POST" });
}

export function getConversation(id: number): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(`/conversations/${id}`);
}
```

- [ ] **Step 4: Write `frontend/src/api/messages.ts`**

```typescript
import { apiFetch, BASE_URL } from "./client";

export interface SendMessageResponse {
  message_id: number;
}

export function sendMessage(
  conversationId: number,
  content: string
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function streamUrl(conversationId: number, messageId: number): string {
  return `${BASE_URL}/conversations/${conversationId}/messages/${messageId}/stream`;
}
```

- [ ] **Step 5: Write failing test for `sendMessage`**

```typescript
// frontend/src/api/messages.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { sendMessage, streamUrl } from "./messages";

describe("sendMessage", () => {
  beforeEach(() => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ message_id: 42 }),
      })
    ) as unknown as typeof fetch;
  });

  it("posts content and returns message_id", async () => {
    const result = await sendMessage(1, "hello");
    expect(result.message_id).toBe(42);
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/conversations/1/messages",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("builds the correct stream url", () => {
    expect(streamUrl(1, 42)).toBe(
      "http://localhost:8000/conversations/1/messages/42/stream"
    );
  });
});
```

Add to `frontend/package.json` scripts: `"test": "vitest run"`. Add a `frontend/vitest.config.ts` if `vite.config.ts` doesn't already include test config:

```typescript
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom" },
});
```

Run: `cd frontend && npm test`
Expected: FAIL — `messages.ts` doesn't exist yet if run before Step 4, or PASS if run after. Run this before Step 4 to confirm red, per TDD: temporarily this task lists Step 4 before Step 5 for readability, but if executing strictly TDD, write this test first and confirm it fails on missing module, then write Step 4's implementation.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS

- [ ] **Step 7: Write `frontend/src/hooks/useSSEStream.ts`**

```typescript
import { useEffect, useRef } from "react";

export function useSSEStream(
  url: string | null,
  onToken: (token: string) => void,
  onDone: () => void
): void {
  const onTokenRef = useRef(onToken);
  const onDoneRef = useRef(onDone);
  onTokenRef.current = onToken;
  onDoneRef.current = onDone;

  useEffect(() => {
    if (!url) return;

    const source = new EventSource(url);
    source.onmessage = (event) => {
      onTokenRef.current(event.data);
    };
    source.addEventListener("done", () => {
      onDoneRef.current();
      source.close();
    });
    source.onerror = () => {
      source.close();
    };

    return () => source.close();
  }, [url]);
}
```

- [ ] **Step 8: Commit**

```bash
cd .. && git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/vitest.config.ts frontend/tsconfig.json frontend/index.html frontend/src/api frontend/src/hooks
git commit -m "feat: scaffold frontend with API client, SSE hook, and tests"
```

---

## Task 7: Frontend chat UI components

**Files:**
- Create: `frontend/src/components/MessageBubble.tsx`
- Create: `frontend/src/components/AgentBadge.tsx`
- Create: `frontend/src/components/EscalationBanner.tsx`
- Create: `frontend/src/components/ChatWindow.tsx`
- Create: `frontend/src/pages/ChatPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/components/MessageBubble.test.tsx`
- Test: `frontend/src/components/EscalationBanner.test.tsx`

**Interfaces:**
- Consumes: `Message`, `ConversationDetail` types (Task 6), `createConversation`, `getConversation`, `sendMessage`, `streamUrl` (Task 6), `useSSEStream` (Task 6)
- Produces: `<ChatPage />` mounted in `App.tsx`

- [ ] **Step 1: Write failing test for `MessageBubble`**

```typescript
// frontend/src/components/MessageBubble.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MessageBubble } from "./MessageBubble";

describe("MessageBubble", () => {
  it("renders user message without agent badge", () => {
    render(
      <MessageBubble
        message={{
          id: 1,
          conversation_id: 1,
          role: "user",
          agent_id: null,
          content: "hi there",
          severity: null,
          escalated: false,
          created_at: "2026-09-21T00:00:00Z",
        }}
      />
    );
    expect(screen.getByText("hi there")).toBeInTheDocument();
    expect(screen.queryByTestId("agent-badge")).not.toBeInTheDocument();
  });

  it("renders agent message with agent badge", () => {
    render(
      <MessageBubble
        message={{
          id: 2,
          conversation_id: 1,
          role: "agent",
          agent_id: 5,
          content: "how can I help",
          severity: null,
          escalated: false,
          created_at: "2026-09-21T00:00:00Z",
        }}
      />
    );
    expect(screen.getByTestId("agent-badge")).toBeInTheDocument();
  });
});
```

Run: `cd frontend && npm test`
Expected: FAIL — `MessageBubble` module doesn't exist

- [ ] **Step 2: Write `frontend/src/components/AgentBadge.tsx`**

```typescript
export function AgentBadge({ agentId }: { agentId: number }) {
  return <span data-testid="agent-badge">Agent #{agentId}</span>;
}
```

- [ ] **Step 3: Write `frontend/src/components/MessageBubble.tsx`**

```typescript
import type { Message } from "../api/conversations";
import { AgentBadge } from "./AgentBadge";

export function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={`message-bubble message-bubble--${message.role}`}>
      {message.role === "agent" && message.agent_id !== null && (
        <AgentBadge agentId={message.agent_id} />
      )}
      <p>{message.content}</p>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS

- [ ] **Step 5: Write failing test for `EscalationBanner`**

```typescript
// frontend/src/components/EscalationBanner.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EscalationBanner } from "./EscalationBanner";

describe("EscalationBanner", () => {
  it("renders nothing when status is active", () => {
    const { container } = render(<EscalationBanner status="active" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders banner when status is escalated", () => {
    render(<EscalationBanner status="escalated" />);
    expect(
      screen.getByText(/moved to a human agent/i)
    ).toBeInTheDocument();
  });
});
```

Run: `cd frontend && npm test`
Expected: FAIL — module doesn't exist

- [ ] **Step 6: Write `frontend/src/components/EscalationBanner.tsx`**

```typescript
export function EscalationBanner({ status }: { status: string }) {
  if (status !== "escalated") return null;
  return (
    <div role="alert" className="escalation-banner">
      This conversation has been moved to a human agent who will take care of it.
    </div>
  );
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS

- [ ] **Step 8: Write `frontend/src/components/ChatWindow.tsx`**

```typescript
import { useState } from "react";
import type { Message } from "../api/conversations";
import { MessageBubble } from "./MessageBubble";

interface ChatWindowProps {
  messages: Message[];
  onSend: (content: string) => void;
  disabled: boolean;
}

export function ChatWindow({ messages, onSend, disabled }: ChatWindowProps) {
  const [draft, setDraft] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim() || disabled) return;
    onSend(draft);
    setDraft("");
  };

  return (
    <div className="chat-window">
      <div className="chat-window__messages">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>
      <form onSubmit={handleSubmit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={disabled}
          placeholder="Type a message..."
        />
        <button type="submit" disabled={disabled}>
          Send
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 9: Write `frontend/src/pages/ChatPage.tsx`**

```typescript
import { useCallback, useEffect, useState } from "react";
import { createConversation, getConversation } from "../api/conversations";
import type { ConversationDetail, Message } from "../api/conversations";
import { sendMessage, streamUrl } from "../api/messages";
import { useSSEStream } from "../hooks/useSSEStream";
import { ChatWindow } from "../components/ChatWindow";
import { EscalationBanner } from "../components/EscalationBanner";

export function ChatPage() {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [streamingUrl, setStreamingUrl] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<number | null>(null);
  const [partialContent, setPartialContent] = useState("");

  useEffect(() => {
    createConversation().then((c) =>
      setConversation({ id: c.id, status: c.status, messages: [] })
    );
  }, []);

  const refreshConversation = useCallback(async () => {
    if (!conversation) return;
    const detail = await getConversation(conversation.id);
    setConversation(detail);
  }, [conversation?.id]);

  useSSEStream(
    streamingUrl,
    (token) => setPartialContent((prev) => prev + token),
    () => {
      setStreamingUrl(null);
      setStreamingMessageId(null);
      setPartialContent("");
      refreshConversation();
    }
  );

  const handleSend = async (content: string) => {
    if (!conversation) return;
    const { message_id } = await sendMessage(conversation.id, content);
    await refreshConversation();
    setStreamingMessageId(message_id);
    setStreamingUrl(streamUrl(conversation.id, message_id));
  };

  if (!conversation) return <div>Loading...</div>;

  const displayMessages: Message[] = streamingMessageId
    ? conversation.messages.map((m) =>
        m.id === streamingMessageId ? { ...m, content: partialContent } : m
      )
    : conversation.messages;

  return (
    <div className="chat-page">
      <EscalationBanner status={conversation.status} />
      <ChatWindow
        messages={displayMessages}
        onSend={handleSend}
        disabled={conversation.status === "escalated"}
      />
    </div>
  );
}
```

- [ ] **Step 10: Update `frontend/src/App.tsx`**

```typescript
import { ChatPage } from "./pages/ChatPage";

function App() {
  return <ChatPage />;
}

export default App;
```

- [ ] **Step 11: Run full frontend test suite**

Run: `cd frontend && npm test`
Expected: PASS (all tests)

- [ ] **Step 12: Manual smoke test**

Run backend: `uv run uvicorn app.main:app --reload --app-dir backend`
Run frontend: `cd frontend && npm run dev`
Open browser, send a message, confirm tokens stream in and final message appears.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/components frontend/src/pages frontend/src/App.tsx
git commit -m "feat: add chat UI components wired to SSE streaming"
```

---

## Task 8: Sync docs per AGENTS.md

**Files:**
- No new files — delegates to subagent

- [ ] **Step 1: Run doc-sync subagent**

Dispatch the `doc-sync` subagent (per CLAUDE.md rule #4 / AGENTS.md rule #4) to scan the diff introduced by Tasks 1-7 and update `IMPLEMENTATION_PLAN.md`, `AGENTS.md` (if needed), and `doc/feature/` with concept docs for: DB models, agent/conversation/message services, streaming service seam, and the frontend chat UI.

- [ ] **Step 2: Review doc-sync output**

Confirm `IMPLEMENTATION_PLAN.md` reflects the new backend/frontend structure and that `doc/feature/index.md` lists the new concept docs.

- [ ] **Step 3: Commit doc updates**

```bash
git add IMPLEMENTATION_PLAN.md AGENTS.md doc/
git commit -m "docs: sync architecture docs with chat app scaffold"
```
