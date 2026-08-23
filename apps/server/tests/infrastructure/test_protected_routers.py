"""The business endpoints must not be reachable without a session.

They expose tax documents and extracted data, so an open API would make the
login decorative.
"""

import pytest
from fastapi.testclient import TestClient

from server.main import app

PROTECTED = [
    ("GET", "/clients"),
    ("POST", "/clients"),
    ("GET", "/documents/doc-1/extracted-data"),
    ("POST", "/document-types"),
]


@pytest.fixture(autouse=True)
def anthropic_auth(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_requires_a_session(client, method, path):
    assert client.request(method, path).status_code == 401


def test_health_stays_open(client):
    assert client.get("/health").status_code == 200


def test_the_drive_webhook_stays_open(client):
    # Google calls it unauthenticated; it is guarded by its own shared secret.
    assert client.post("/webhooks/drive").status_code != 401
