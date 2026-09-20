import asyncio
from collections.abc import AsyncIterator

_STUB_TOKENS = ["Thanks ", "for ", "your ", "message. ", "This ", "is ", "a ", "stub ", "reply."]


async def generate_reply(user_content: str) -> AsyncIterator[str]:
    for token in _STUB_TOKENS:
        await asyncio.sleep(0.01)
        yield token
