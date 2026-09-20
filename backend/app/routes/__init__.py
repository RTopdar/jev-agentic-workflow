from fastapi import APIRouter

from app.controllers.agent_controller import router as agent_router
from app.controllers.conversation_controller import router as conversation_router
from app.controllers.message_controller import router as message_router

api_router = APIRouter()
api_router.include_router(agent_router)
api_router.include_router(conversation_router)
api_router.include_router(message_router)
