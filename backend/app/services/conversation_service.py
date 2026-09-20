from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


async def create_conversation(session: AsyncSession) -> Conversation:
    conversation = Conversation()
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def get_conversation(
    session: AsyncSession, conversation_id: int
) -> Conversation | None:
    return await session.get(Conversation, conversation_id)


async def get_messages(session: AsyncSession, conversation_id: int) -> list[Message]:
    result = await session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    return list(result.all())


async def set_status(
    session: AsyncSession, conversation: Conversation, status: str
) -> Conversation:
    conversation.status = status
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation
