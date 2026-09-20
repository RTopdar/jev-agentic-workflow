import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.db import session as db_session


@pytest_asyncio.fixture(autouse=True)
async def _test_engine():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    db_session.engine = test_engine
    yield
    await test_engine.dispose()
