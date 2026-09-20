from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Agent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
