from fastapi.testclient import TestClient

from server.infrastructure.api import deps
from server.main import app


def test_allows_cross_origin_requests_from_the_web_app() -> None:
    client = TestClient(app)
    web_app_url = deps.get_settings().web_app_url

    response = client.get("/clients", headers={"Origin": web_app_url})

    assert response.headers["access-control-allow-origin"] == web_app_url


def test_rejects_unlisted_origins() -> None:
    client = TestClient(app)

    response = client.get("/clients", headers={"Origin": "http://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers
