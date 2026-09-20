import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_post_message_creates_user_and_pending_agent_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        conv_resp = await client.post("/conversations")
        conv_id = conv_resp.json()["id"]

        resp = await client.post(
            f"/conversations/{conv_id}/messages", json={"content": "hello"}
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "message_id" in body

        conv = await client.get(f"/conversations/{conv_id}")
        messages = conv.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hello"
        assert messages[1]["role"] == "agent"
        assert messages[1]["id"] == body["message_id"]
