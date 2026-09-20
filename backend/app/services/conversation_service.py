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


async def list_conversations(session: AsyncSession) -> list[tuple[Conversation, str | None]]:
    result = await session.exec(select(Conversation))
    conversations = list(result.all())

    rows: list[tuple[Conversation, str | None, object]] = []
    for conversation in conversations:
        first_user_message = await session.exec(
            select(Message)
            .where(Message.conversation_id == conversation.id, Message.role == "user")
            .order_by(Message.id)
            .limit(1)
        )
        message = first_user_message.first()
        preview = message.content[:80] if message else None

        last_message = await session.exec(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.id.desc())
            .limit(1)
        )
        last_activity = last_message.first()
        last_activity_at = (
            last_activity.created_at if last_activity else conversation.created_at
        )
        rows.append((conversation, preview, last_activity_at))

    rows.sort(key=lambda row: row[2], reverse=True)
    return [(conversation, preview) for conversation, preview, _ in rows]


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
