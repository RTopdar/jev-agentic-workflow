from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.services import conversation_service, message_service

router = APIRouter(prefix="/conversations", tags=["messages"])


class MessageCreate(BaseModel):
    content: str


class MessageCreateResponse(BaseModel):
    message_id: int


@router.post(
    "/{conversation_id}/messages", response_model=MessageCreateResponse, status_code=201
)
async def post_message(
    conversation_id: int,
    payload: MessageCreate,
    session: AsyncSession = Depends(get_session),
) -> MessageCreateResponse:
    conversation = await conversation_service.get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await message_service.create_user_message(session, conversation_id, payload.content)
    pending = await message_service.create_pending_agent_message(
        session, conversation_id
    )
    return MessageCreateResponse(message_id=pending.id)
