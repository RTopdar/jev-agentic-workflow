"""Orchestrator that chains intent classification with tool execution."""

from typing import Any, Callable
import logging
from middleware import AutoModeMiddleware, IntentMode


logger = logging.getLogger(__name__)


class ToolExecutor:
    """Wraps tool execution with middleware gating."""

    def __init__(self, tool_name: str, func: Callable):
        self.tool_name = tool_name
        self.func = func

    async def __call__(self, *args, **kwargs) -> Any:
        """Execute tool directly (no gating in base executor)."""
        return await self.func(*args, **kwargs)


class GatedToolExecutor(ToolExecutor):
    """Tool executor that gates execution via auto-mode middleware."""

    def __init__(
        self,
        tool_name: str,
        func: Callable,
        middleware: AutoModeMiddleware,
    ):
        super().__init__(tool_name, func)
        self.middleware = middleware

    async def __call__(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> Any:
        """
        Gate tool execution based on classified intent.

        Args:
            user_input: User's request
            context: Optional context for classification
            *args, **kwargs: Arguments to pass to tool function

        Returns:
            Tool result if allowed, else None with rejection logged
        """
        allowed, reason = await self.middleware.can_execute_tool(
            self.tool_name,
            user_input,
            context,
        )

        logger.info(f"Tool '{self.tool_name}' gate: {reason}")

        if not allowed:
            logger.warning(f"Tool execution blocked: {reason}")
            return None

        logger.info(f"Executing '{self.tool_name}'")
        return await self.func(*args, **kwargs)


class WorkflowOrchestrator:
    """Orchestrates multi-step workflows with intent-gated tool execution."""

    def __init__(self, middleware: AutoModeMiddleware):
        self.middleware = middleware
        self.tools: dict[str, ToolExecutor] = {}

    def register_tool(
        self,
        name: str,
        func: Callable,
        gated: bool = False,
    ) -> None:
        """
        Register tool with optional gating.

        Args:
            name: Tool identifier
            func: Async callable
            gated: If True, use GatedToolExecutor; else plain ToolExecutor
        """
        if gated:
            executor = GatedToolExecutor(name, func, self.middleware)
        else:
            executor = ToolExecutor(name, func)

        self.tools[name] = executor
        logger.info(f"Registered tool '{name}' (gated={gated})")

    async def execute_step(
        self,
        tool_name: str,
        user_input: str,
        context: dict[str, Any] | None = None,
        **tool_kwargs,
    ) -> Any:
        """
        Execute a single workflow step.

        Args:
            tool_name: Name of registered tool
            user_input: User's request context
            context: Classification context
            **tool_kwargs: Arguments to pass to tool

        Returns:
            Tool result
        """
        executor = self.tools.get(tool_name)
        if not executor:
            raise ValueError(f"Tool '{tool_name}' not registered")

        if isinstance(executor, GatedToolExecutor):
            return await executor(user_input, context, **tool_kwargs)
        else:
            return await executor(**tool_kwargs)

    async def execute_workflow(
        self,
        steps: list[dict[str, Any]],
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Execute multi-step workflow with shared context.

        Args:
            steps: List of step specs {tool_name, kwargs}
            user_input: User's overall request
            context: Shared context for all steps

        Returns:
            List of step results
        """
        results = []

        for i, step in enumerate(steps):
            tool_name = step.get("tool_name")
            tool_kwargs = step.get("kwargs", {})

            logger.info(f"Step {i + 1}/{len(steps)}: executing '{tool_name}'")

            result = await self.execute_step(
                tool_name,
                user_input,
                context,
                **tool_kwargs,
            )

            results.append(result)

            if result is None and isinstance(
                self.tools[tool_name], GatedToolExecutor
            ):
                logger.warning(f"Step {i + 1} blocked by middleware, halting workflow")
                break

        return results
