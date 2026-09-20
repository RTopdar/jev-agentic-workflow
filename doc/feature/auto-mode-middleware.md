---
type: Module
title: Auto-Mode Middleware
description: Jev-powered intent classification and tool access control
resource: middleware.py, orchestrator.py
tags: [middleware, safety, jev, intent-classification]
status: alpha
---

## Overview

Auto-mode middleware classifies user intent (safe/risky/dangerous) using TypeSafe's Jev and gates tool execution based on classified intent. Implements least-privilege access patterns where code owns control flow and Jev provides semantic understanding.

## Design

**Intent Classification:**
- User request → Jev's `Choice` primitive → (mode: safe|risky|dangerous, confidence: 0.0–1.0)
- Confidence threshold (60%) blocks ambiguous requests regardless of classified mode
- Requests below threshold escalated (blocked from dangerous tools)

**Tool Gating:**
- Each tool has `allowed_modes`: set of `IntentMode` values that permit execution
- Example: `bash` allows only `SAFE` mode; `delete` allows only `SAFE` mode; `read` has no restrictions
- Gate decision: if classified mode ∉ allowed_modes OR confidence < 0.6 → block

## Components

### `AutoModeMiddleware`

```python
class AutoModeMiddleware:
    def __init__(api_key: str | None, dangerous_tools: list[str])
    async def classify_intent(user_input: str, context: dict) → (IntentMode, float)
    async def can_execute_tool(tool_name: str, user_input: str, context: dict) → (bool, str)
```

**Methods:**
- `classify_intent()`: Calls Jev with user input and context, returns (intent_mode, confidence)
- `can_execute_tool()`: Checks tool gate, returns (allowed, reason_string)

### `ToolGate`

```python
@dataclass
class ToolGate:
    tool_name: str
    allowed_modes: set[IntentMode]
    reason: str
```

Access control rule: tool is executable only when classified intent is in `allowed_modes`.

### `WorkflowOrchestrator`

```python
class WorkflowOrchestrator:
    def register_tool(name: str, func: Callable, gated: bool = False)
    async def execute_step(tool_name: str, user_input: str, context: dict, **kwargs) → Any
    async def execute_workflow(steps: list, user_input: str, context: dict) → list[Any]
```

Chains multiple gated/ungated tools. Halts on first blocked step (when a gated tool returns None).

### `ToolExecutor` / `GatedToolExecutor`

- `ToolExecutor`: Direct execution wrapper (no gating)
- `GatedToolExecutor`: Wraps execution with `can_execute_tool()` check before running

## Example Usage

```python
middleware = AutoModeMiddleware(dangerous_tools=["bash", "delete"])
orchestrator = WorkflowOrchestrator(middleware)

orchestrator.register_tool("bash", bash_func, gated=True)
orchestrator.register_tool("read", read_func, gated=False)

# Safe request: allowed
allowed, reason = await middleware.can_execute_tool(
    "bash",
    "List files in directory",
)
# Returns (True, "allowed under safe mode (confidence: 0.95)")

# Dangerous request: blocked
allowed, reason = await middleware.can_execute_tool(
    "bash",
    "Delete all system files",
)
# Returns (False, "bash blocked: intent classified as dangerous...")
```

## Testing

Full test suite in `test_middleware.py`:
- Intent classification (safe, risky, dangerous)
- Tool gating logic
- Confidence thresholding
- Multi-step workflows with early halt on block
- Ungated vs. gated executor behavior

Run: `pytest test_middleware.py -v`

## Open Questions

- Should confidence threshold be per-gate or global? Currently global (60%).
- Escalation path for blocked requests: log only, or route to human review queue?
- Intent caching: should identical requests reuse past classifications?

## Related

- [LangChain TypeSafe Integration](https://www.langchain.com/blog/building-a-harness-with-jev)
- [TypeSafe System One Architecture](https://docs.typesafe.ai/concepts/system-one.md)
