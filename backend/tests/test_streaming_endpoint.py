import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_stream_reply_emits_tokens_and_finalizes_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        conv_resp = await client.post("/conversations")
        conv_id = conv_resp.json()["id"]
        msg_resp = await client.post(
            f"/conversations/{conv_id}/messages", json={"content": "hello"}
        )
        message_id = msg_resp.json()["message_id"]

        async with client.stream(
            "GET", f"/conversations/{conv_id}/messages/{message_id}/stream"
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            body = ""
            async for chunk in resp.aiter_text():
                body += chunk
            assert "data:" in body

        conv = await client.get(f"/conversations/{conv_id}")
        agent_message = conv.json()["messages"][1]
        assert agent_message["content"] != ""
