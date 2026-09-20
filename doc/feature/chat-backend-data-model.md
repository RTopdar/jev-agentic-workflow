---
type: Module
title: Chat App Data Model
description: SQLModel tables for the chat app scaffold (Agent, Conversation, Message)
resource: backend/app/models/
tags: [backend, sqlmodel, postgres, data-model, chat-app]
status: alpha
---

## Overview

Three SQLModel tables back the chat app scaffold. All are plain data tables today — no relationships enforced beyond foreign keys, no business logic on the models themselves (that lives in `services/`, see [Chat App Service Layer](/doc/feature/chat-backend-services.md)).

## Tables

### `Agent` (`backend/app/models/agent.py`)

- `id: int | None` — primary key
- `name: str`
- `description: str`
- `created_at: datetime`

Represents a distinct chat agent persona. `name` + `description` are the fields the future Jev `Choice`-based router will read to pick an agent for a given conversation turn (not implemented yet — see the streaming seam doc).

### `Conversation` (`backend/app/models/conversation.py`)

- `id: int | None` — primary key
- `status: str` — defaults to `"active"`; `"escalated"` is the other value currently referenced (by the frontend's `EscalationBanner`/disabled-input logic), though nothing server-side sets it yet
- `created_at: datetime`

### `Message` (`backend/app/models/message.py`)

- `id: int | None` — primary key
- `conversation_id: int` — FK → `conversation.id`
- `role: str` — `"user"` or `"agent"`
- `agent_id: int | None` — FK → `agent.id`, set when `role == "agent"` (not populated yet by any service)
- `content: str`
- `severity: float | None` — reserved for future Jev `Score`-based escalation logic
- `escalated: bool` — defaults to `False`; reserved for the same
- `created_at: datetime`

## Design Notes

- `created_at` uses `datetime.utcnow` as a naive-UTC default (fixed to be tz-naive consistently across all three tables per commit `b66e2d1`, to avoid Postgres tz-aware/naive comparison errors).
- No `Agent`/`Conversation`/`Message` ORM relationships (`sqlmodel.Relationship`) are declared; all cross-table reads go through explicit `select()` queries in `services/`.
- Tables are created via `SQLModel.metadata.create_all` at app startup (`db/session.py: init_db()`) for local/dev use; `backend/alembic/` carries the authoritative migration (`1dde6dca8bbb_initial_tables.py`) for anything beyond dev.

## Open Questions

- `severity`/`escalated` on `Message` and `status` on `Conversation` are currently write-only-by-nobody — no code path sets them. They exist to satisfy the frontend contract ahead of the Jev scoring integration landing.

## Related

- [Chat App Service Layer](/doc/feature/chat-backend-services.md)
- [Chat Reply Streaming Seam](/doc/feature/chat-streaming-seam.md)
