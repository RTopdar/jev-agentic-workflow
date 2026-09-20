"""Example: auto-mode middleware in action."""

import asyncio
import logging
from middleware import AutoModeMiddleware
from orchestrator import WorkflowOrchestrator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def bash_tool(command: str) -> str:
    """Simulated bash execution."""
    return f"[bash] executed: {command}"


async def read_file_tool(path: str) -> str:
    """Simulated file read."""
    return f"[read] {path}: mock content"


async def delete_tool(path: str) -> str:
    """Simulated deletion."""
    return f"[delete] removed: {path}"


async def main():
    """Demonstrate auto-mode middleware gating."""
    middleware = AutoModeMiddleware(dangerous_tools=["bash", "delete"])
    orchestrator = WorkflowOrchestrator(middleware)

    orchestrator.register_tool("bash", bash_tool, gated=True)
    orchestrator.register_tool("read", read_file_tool, gated=False)
    orchestrator.register_tool("delete", delete_tool, gated=True)

    print("\n=== Scenario 1: Safe read request ===")
    user_input = "Can you read the config file?"
    context = {"environment": "development"}

    result = await orchestrator.execute_step(
        "read",
        user_input,
        context,
        path="/etc/config.yaml",
    )
    logger.info(f"Result: {result}")

    print("\n=== Scenario 2: Safe shell command ===")
    user_input = "Run ls to list the files"
    result = await orchestrator.execute_step(
        "bash",
        user_input,
        context,
        command="ls -la",
    )
    logger.info(f"Result: {result}")

    print("\n=== Scenario 3: Multi-step workflow ===")
    user_input = "Read the config and then delete it"
    workflow_steps = [
        {
            "tool_name": "read",
            "kwargs": {"path": "/tmp/old_config.yaml"},
        },
        {
            "tool_name": "delete",
            "kwargs": {"path": "/tmp/old_config.yaml"},
        },
    ]

    results = await orchestrator.execute_workflow(workflow_steps, user_input, context)
    logger.info(f"Workflow results: {results}")

    print("\n=== Scenario 4: Ambiguous request (low confidence) ===")
    user_input = "Do something with that file"
    result = await orchestrator.execute_step(
        "delete",
        user_input,
        context,
        path="/tmp/mystery.txt",
    )
    logger.info(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
