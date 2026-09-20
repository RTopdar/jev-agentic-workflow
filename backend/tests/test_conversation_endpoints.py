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


@pytest.mark.asyncio
async def test_list_conversations_includes_preview():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = (await client.post("/conversations")).json()
        second = (await client.post("/conversations")).json()

        await client.post(
            f"/conversations/{first['id']}/messages", json={"content": "hello there"}
        )

        resp = await client.get("/conversations")
        assert resp.status_code == 200
        rows = {row["id"]: row for row in resp.json()}

        assert rows[first["id"]]["preview"] == "hello there"
        assert rows[second["id"]]["preview"] is None


@pytest.mark.asyncio
async def test_list_conversations_sorted_by_last_activity():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        older = (await client.post("/conversations")).json()
        newer = (await client.post("/conversations")).json()

        # Bump the older conversation with a new message — it should now
        # sort above the newer, otherwise-untouched conversation.
        await client.post(
            f"/conversations/{older['id']}/messages", json={"content": "ping"}
        )

        resp = await client.get("/conversations")
        rows = resp.json()

        assert rows[0]["id"] == older["id"]
        assert rows[1]["id"] == newer["id"]
