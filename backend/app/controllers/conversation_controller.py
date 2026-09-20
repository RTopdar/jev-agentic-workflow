from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.models.conversation import Conversation
from app.models.message import Message
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationDetail(BaseModel):
    id: int
    status: str
    messages: list[Message]


@router.post("", response_model=Conversation, status_code=201)
async def create_conversation(
    session: AsyncSession = Depends(get_session),
) -> Conversation:
    return await conversation_service.create_conversation(session)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int, session: AsyncSession = Depends(get_session)
) -> ConversationDetail:
    conversation = await conversation_service.get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await conversation_service.get_messages(session, conversation_id)
    return ConversationDetail(
        id=conversation.id, status=conversation.status, messages=messages
    )
