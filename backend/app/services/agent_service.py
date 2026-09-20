from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent import Agent


async def create_agent(session: AsyncSession, name: str, description: str) -> Agent:
    agent = Agent(name=name, description=description)
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def list_agents(session: AsyncSession) -> list[Agent]:
    result = await session.exec(select(Agent))
    return list(result.all())
