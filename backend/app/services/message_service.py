from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.message import Message


async def create_user_message(
    session: AsyncSession, conversation_id: int, content: str
) -> Message:
    message = Message(conversation_id=conversation_id, role="user", content=content)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def create_pending_agent_message(
    session: AsyncSession, conversation_id: int
) -> Message:
    message = Message(conversation_id=conversation_id, role="agent", content="")
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def get_message(session: AsyncSession, message_id: int) -> Message | None:
    return await session.get(Message, message_id)


async def finalize_agent_message(
    session: AsyncSession, message: Message, content: str
) -> Message:
    message.content = content
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message
