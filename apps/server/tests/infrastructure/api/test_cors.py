from fastapi.testclient import TestClient

from server.main import app


def test_allows_cross_origin_requests_from_the_web_app() -> None:
    client = TestClient(app)

    response = client.get("/clients", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_rejects_unlisted_origins() -> None:
    client = TestClient(app)

    response = client.get("/clients", headers={"Origin": "http://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers
