from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


async def test_root() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["api"] == "/api/v1"


async def test_request_id_se_propaga() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})

    assert response.headers["X-Request-ID"] == "abc-123"


async def test_404_es_problem_json() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/api/v1/no-existe")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"

    problem = response.json()
    assert problem["status"] == 404
    assert problem["code"] == "NO_ENCONTRADO"
    assert problem["title"] == "Recurso no encontrado"
    assert problem["instance"] == "/api/v1/no-existe"
    assert problem["type"].endswith("/no-encontrado")
    assert problem["request_id"]


async def test_metodo_no_permitido_es_problem_json() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "METODO_NO_PERMITIDO"
