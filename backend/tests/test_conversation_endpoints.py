import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_and_get_conversation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/conversations")
        assert resp.status_code == 201
        conv = resp.json()
        assert conv["status"] == "active"

        resp = await client.get(f"/conversations/{conv['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == conv["id"]
        assert body["messages"] == []
