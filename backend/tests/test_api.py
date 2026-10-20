import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    settings = Settings(
        _env_file=None,
        cors_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    )
    transport = ASGITransport(app=create_app(settings))
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


async def test_health_returns_ok(client):
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_swagger_and_openapi_expose_health_response_schema(client):
    docs = await client.get("/docs")
    assert docs.status_code == 200
    assert "swagger-ui" in docs.text

    response = await client.get("/openapi.json")
    assert response.status_code == 200
    document = response.json()
    response_schema = document["paths"]["/api/v1/health"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]
    schema_name = response_schema["$ref"].rsplit("/", 1)[-1]
    assert "status" in document["components"]["schemas"][schema_name]["properties"]


@pytest.mark.parametrize(
    "origin", ["http://localhost:5173", "http://127.0.0.1:5173"]
)
async def test_default_frontend_origins_allow_credentialed_preflight(client, origin):
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    methods = {
        method.strip()
        for method in response.headers["access-control-allow-methods"].split(",")
    }
    assert methods == {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


async def test_configured_lan_frontend_origin_is_allowed():
    origin = "http://192.168.1.20:5173"
    settings = Settings(_env_file=None, cors_origins=[origin])
    transport = ASGITransport(app=create_app(settings))
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/api/v1/health",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


async def test_untrusted_origin_preflight_is_rejected(client):
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://untrusted.example:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


async def test_untrusted_origin_get_has_no_cors_permission(client):
    response = await client.get(
        "/api/v1/health", headers={"Origin": "http://untrusted.example:5173"}
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
