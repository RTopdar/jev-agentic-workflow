---
type: Module
title: Chat Frontend UI
description: React + Vite single-conversation chat UI consuming the backend REST/SSE API
resource: frontend/src/
tags: [frontend, react, vite, sse, chat-app]
status: alpha
---

## Overview

A single-conversation React chat UI (`frontend/src/`) with no auth and no conversation list — it creates one conversation on load and talks to it for the session. Treats the backend purely as a REST + SSE API; no shared types/code with `backend/`.

## Structure

- **`api/`** — `client.ts` (base fetch wrapper), `conversations.ts` (`createConversation`, `getConversation`), `messages.ts` (`sendMessage`, `streamUrl`)
- **`hooks/useSSEStream.ts`** — wraps the browser `EventSource` API: takes a nullable URL, an `onToken` callback (fired per `message` event) and an `onDone` callback (fired on the `done` event, then closes the connection); re-subscribes whenever `url` changes.
- **`components/`** — `MessageBubble` (renders one message), `AgentBadge`, `EscalationBanner` (shown based on `conversation.status`), `ChatWindow` (message list + input, disabled when passed `disabled`)
- **`pages/ChatPage.tsx`** — top-level page:
  1. Creates a conversation on mount.
  2. `handleSend` posts a user message, refreshes conversation state, then opens an SSE stream (`useSSEStream`) against the returned pending `message_id`.
  3. Appends streamed tokens into local `partialContent` state, substituting it into the matching message in the displayed list while streaming.
  4. On stream completion, clears streaming state and re-fetches the conversation so the finalized agent message replaces the local partial one.
  5. Disables the chat input when `conversation.status === "escalated"`.

## Design Notes

- No polling — the only way new content appears is via the SSE stream triggered right after a send; there is no live-refresh of a conversation being viewed passively.
- Component-level tests exist for `MessageBubble` and `EscalationBanner`; `api/messages.ts` has a request-shape test.

## Open Questions

- No handling yet for `EventSource` `onerror` beyond closing the connection (no retry/backoff or user-facing error state).

## Related

- [Chat App Backend — Routes, Controllers, Services](/doc/feature/chat-backend-services.md)
- [Chat Reply Streaming Seam](/doc/feature/chat-streaming-seam.md)
