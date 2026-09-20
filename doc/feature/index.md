---
type: Bundle Index
title: jev-agentic-workflow architecture
description: OKF bundle indexing this project's modules, services, and scripts.
status: stable
---

# jev-agentic-workflow — Architecture Bundle

OKF (Open Knowledge Format v0.2) bundle. Each file below is one concept document. Traverse via links, not by reading the repo's source tree directly, when answering "how does X work" questions.

## Overview

**Start here:**
- [Architecture Overview](/doc/feature/architecture_overview.md) — high-level system design (create this first)

## Concepts

- [Auto-Mode Middleware](/doc/feature/auto-mode-middleware.md) — middleware.py, orchestrator.py, Jev-powered intent classification and tool access control
- [Chat App Data Model](/doc/feature/chat-backend-data-model.md) — SQLModel `Agent`/`Conversation`/`Message` tables backing the chat app scaffold
- [Chat App Backend — Routes, Controllers, Services](/doc/feature/chat-backend-services.md) — FastAPI MVC-ish layering, endpoints, config/session setup
- [Chat Reply Streaming Seam](/doc/feature/chat-streaming-seam.md) — stub `streaming_service.py` + SSE endpoint, attachment point for the future langgraph + Jev agent layer
- [Chat Frontend UI](/doc/feature/chat-frontend-ui.md) — React + Vite single-conversation chat UI, SSE consumption

## Related

- [doc/index.md](/doc/index.md) — index of indexes for both `doc/` bundles
- [doc/bug/index.md](/doc/bug/index.md) — incident index (bug side of `doc/`)
- [IMPLEMENTATION_PLAN.md](/IMPLEMENTATION_PLAN.md) — narrative architecture + open decisions (kept in sync by the doc-sync agent)
