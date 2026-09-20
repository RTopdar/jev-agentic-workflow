from datetime import datetime

from sqlmodel import Field, SQLModel


class Agent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
