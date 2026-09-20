"""Jev agentic workflow — TypeSafe-powered auto-mode middleware."""

import asyncio
from example_usage import main as run_example


async def main():
    """Entry point for jev-agentic-workflow."""
    print("Starting jev-agentic-workflow with auto-mode middleware...\n")
    await run_example()


if __name__ == "__main__":
    asyncio.run(main())
