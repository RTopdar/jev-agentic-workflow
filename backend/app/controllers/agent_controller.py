from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.models.agent import Agent
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str
    description: str


@router.post("", response_model=Agent, status_code=201)
async def create_agent(
    payload: AgentCreate, session: AsyncSession = Depends(get_session)
) -> Agent:
    return await agent_service.create_agent(session, payload.name, payload.description)


@router.get("", response_model=list[Agent])
async def list_agents(session: AsyncSession = Depends(get_session)) -> list[Agent]:
    return await agent_service.list_agents(session)
