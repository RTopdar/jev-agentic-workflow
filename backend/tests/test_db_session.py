import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


class _Dummy(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


@pytest.mark.asyncio
async def test_session_can_write_and_read():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        session.add(_Dummy(name="hello"))
        await session.commit()

    async with AsyncSession(engine) as session:
        from sqlmodel import select

        result = await session.exec(select(_Dummy))
        rows = result.all()
        assert len(rows) == 1
        assert rows[0].name == "hello"
