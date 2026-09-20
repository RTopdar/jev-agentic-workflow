from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.services import conversation_service, message_service, streaming_service

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


@router.get("/{conversation_id}/messages/{message_id}/stream")
async def stream_message_reply(
    conversation_id: int,
    message_id: int,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    message = await message_service.get_message(session, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    async def event_stream():
        full_content = ""
        async for token in streaming_service.generate_reply(""):
            full_content += token
            yield f"data: {token}\n\n"
        await message_service.finalize_agent_message(session, message, full_content)
        yield "event: done\ndata: end\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
