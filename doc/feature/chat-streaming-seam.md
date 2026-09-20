---
type: Module
title: Chat Reply Streaming Seam
description: Stub streaming_service.py and its SSE endpoint — the attachment point for the future langgraph + Jev agent layer
resource: backend/app/services/streaming_service.py, backend/app/controllers/message_controller.py
tags: [backend, sse, streaming, jev, langgraph, stub, chat-app]
status: stub
---

## Overview

`streaming_service.generate_reply()` is a deliberate stub: it ignores its input and yields a fixed list of canned tokens (`"Thanks ", "for ", "your ", "message. ", ...`) with a small `asyncio.sleep(0.01)` between each, simulating token-by-token generation. This is the explicit seam where the real AI layer will be wired in — **not implemented in this branch.**

## Current Behavior

- `GET /conversations/{conversation_id}/messages/{message_id}/stream` (in `message_controller.py`) looks up the pending agent `Message` row, then streams `generate_reply("")` as Server-Sent Events: one `data: <token>` event per token, followed by `event: done\ndata: end`.
- On completion, the full concatenated content is written back via `message_service.finalize_agent_message`, replacing the empty placeholder content.
- The controller currently calls `generate_reply("")` — the real conversation content isn't threaded through yet, since the stub ignores its argument anyway.

## Planned Design (per `docs/superpowers/specs/2026-09-21-chat-app-scaffold-design.md`, not yet implemented)

- **Agent routing**: Jev `Choice`, reading each `Agent.name`/`Agent.description` plus the last 5 messages of the conversation, selects which agent should respond.
- **Severity / escalation scoring**: Jev `Score` evaluates the conversation/response to set `Message.severity` and `Message.escalated`, and presumably `Conversation.status = "escalated"` (consumed today by the frontend's `EscalationBanner` and input-disable logic, but nothing sets it yet).
- langgraph is expected to orchestrate the above around the existing SSE token-stream shape, so the endpoint contract (`data:` / `event: done`) should not need to change.

## Design Notes

- Swapping the stub for the real pipeline should only require changing `streaming_service.py`'s internals — the controller's SSE framing and the `finalize_agent_message` handoff are already the shape the real implementation would need.

## Open Questions

- Whether agent selection happens before or after the user message is persisted (affects whether `Message.agent_id` is set at creation vs. finalization time).
- Whether `Conversation.status` transitions to `"escalated"` happen synchronously in this endpoint or via a separate scoring step.

## Related

- [Chat App Backend — Routes, Controllers, Services](/doc/feature/chat-backend-services.md)
- [Chat App Data Model](/doc/feature/chat-backend-data-model.md)
- [Chat Frontend UI](/doc/feature/chat-frontend-ui.md)
