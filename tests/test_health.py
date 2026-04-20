from httpx import AsyncClient


async def test_health_check_returns_200(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200


async def test_health_check_returns_ok_status(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.json()["status"] == "ok"