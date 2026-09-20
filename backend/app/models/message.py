from datetime import datetime

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id")
    role: str
    agent_id: int | None = Field(default=None, foreign_key="agent.id")
    content: str
    severity: float | None = Field(default=None)
    escalated: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
