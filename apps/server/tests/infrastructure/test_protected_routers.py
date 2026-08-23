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
    # Google calls it unauthenticated; it is guarded by its own per-channel
    # shared secret, not a session cookie.
    from datetime import UTC, datetime

    from server.domain.entities import DriveWatchChannel
    from server.infrastructure.adapters.in_memory_repositories import (
        InMemoryDriveWatchChannelRepository,
    )
    from server.infrastructure.api import deps

    channels = InMemoryDriveWatchChannelRepository()
    channels.save(
        DriveWatchChannel(
            id="channel-1",
            resource_id="resource-1",
            folder_id="folder-1",
            client_id="client-1",
            token="shared-secret",
            page_token="token-1",
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    class FakeProcessDriveChangeNotification:
        def execute(self, channel_id: str, resource_state: str) -> list:
            return []

    app.dependency_overrides[deps.get_process_drive_change_notification_use_case] = lambda: (
        FakeProcessDriveChangeNotification()
    )
    app.dependency_overrides[deps.get_drive_watch_channel_repository] = lambda: channels

    response = client.post(
        "/webhooks/drive",
        headers={"X-Goog-Channel-Token": "shared-secret", "X-Goog-Channel-Id": "channel-1"},
    )

    app.dependency_overrides.clear()

    assert response.status_code != 401
