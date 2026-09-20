# Implementation Plan — jev-agentic-workflow

Narrative architecture and open decisions for this project. Kept in sync with the codebase by the doc-sync flow (AGENTS.md rule #4). Treat drift between this file and the actual code as a bug.

## Status

Alpha — auto-mode middleware functional. Orchestrator supports multi-step workflows with intent-gated tool execution. Full test suite in place.

## Dependencies

- **pydantic** (2.13.5) — data validation and serialization
- **pydantic-settings** (2.15.0) — environment-based config management
- **langchain-typesafe** (0.0.1a3) — LangChain integration with TypeSafe System One models (jev)
- **pytest** (7.4+) — test framework
- **pytest-asyncio** (0.21+) — async test support

## Components

- **middleware.py** — `AutoModeMiddleware` class using Jev for intent classification (safe/risky/dangerous) and `ToolGate` config for access control
- **orchestrator.py** — `WorkflowOrchestrator` chains intent-gated tools in multi-step workflows; `ToolExecutor` (ungated) and `GatedToolExecutor` (permission-checked)
- **example_usage.py** — runnable scenarios: safe read, safe bash, multi-step workflow, low-confidence blocking
- **test_middleware.py** — pytest suite for middleware intent classification, tool gating, orchestration workflows
- **main.py** — entry point that runs example scenarios

## Architecture

**Intent Classification Pipeline:**

1. User request → Jev's `Choice` primitive classifies intent (safe/risky/dangerous) with confidence
2. Tool gate checks intent against allowed modes (e.g., bash only allowed in SAFE mode)
3. Low-confidence (<60%) requests blocked regardless of mode
4. Orchestrator chains multiple gated steps, halting on first blocked step

**Key Design:**

- Jev makes the judgment; code owns control flow (requests denied at the gate, not by model refusal)
- Tool registration separates ungated (read) from gated (bash/delete) operations
- Confidence thresholding prevents ambiguous requests reaching dangerous tools
- Multi-step workflows share user intent context across steps

## Open Decisions

- Confidence threshold (60%) — tunable per gate or global?
- Escalation path for blocked requests — log only, or route to human review?
- Intent cache — should repeated identical requests reuse classification?

## Changelog

- 2026-09-21: Added auto-mode middleware stack (middleware.py, orchestrator.py, example_usage.py, test_middleware.py); full pytest suite; updated pyproject.toml with dev dependencies.
