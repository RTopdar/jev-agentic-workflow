import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_and_list_agents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/agents", json={"name": "Billing Bot", "description": "Handles billing"}
        )
        assert resp.status_code == 201
        created = resp.json()
        assert created["name"] == "Billing Bot"
        assert "id" in created

        resp = await client.get("/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert any(a["id"] == created["id"] for a in agents)
