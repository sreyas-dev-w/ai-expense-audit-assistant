"""Live health liveness + Postgres readiness checks."""
import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from app.api.health import router as health_router


def _health_app() -> FastAPI:
    application = FastAPI()
    application.include_router(health_router, prefix="/api/v1")
    return application


@pytest.fixture
async def client():
    transport = ASGITransport(app=_health_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_liveness_does_not_require_database(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_pings_postgres(client):
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok", "database": "ok"}
