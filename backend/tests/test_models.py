from datetime import datetime

from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message


def test_agent_fields():
    a = Agent(name="Billing Bot", description="Handles billing questions")
    assert a.name == "Billing Bot"
    assert a.description == "Handles billing questions"
    assert a.id is None


def test_conversation_defaults_to_active():
    c = Conversation()
    assert c.status == "active"


def test_message_fields_and_defaults():
    m = Message(conversation_id=1, role="user", content="hi")
    assert m.agent_id is None
    assert m.severity is None
    assert m.escalated is False
    assert isinstance(m.created_at, datetime)
