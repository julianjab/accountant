from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.application.use_cases import (
    ProcessDriveChangeNotification,
    ProcessUploadedDocumentInput,
    SubscribeDriveWebhook,
)
from server.domain.entities import (
    Document,
    DocumentStatus,
    DriveChangedFile,
    DriveChangesPage,
    DriveWatchChannel,
    DriveWatchRegistration,
)
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentRepository,
    InMemoryDriveWatchChannelRepository,
)
from server.infrastructure.api import deps
from server.infrastructure.api.auth_dependency import require_session
from server.main import app

CHANNEL_TOKEN = "channel-secret"


@pytest.fixture(autouse=True)
def anthropic_auth(monkeypatch):
    # The app's lifespan fails fast when no AI auth is configured.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


class FakeProcessUploadedDocument:
    def __init__(self) -> None:
        self.calls: list[ProcessUploadedDocumentInput] = []

    def execute(self, data: ProcessUploadedDocumentInput) -> Document:
        self.calls.append(data)
        return Document(
            id="doc-1",
            client_id=data.client_id,
            document_type_id=None,
            drive_file_id=data.drive_file_id,
            file_name="invoice.pdf",
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            error=None,
            created_at=datetime.now(UTC),
        )


class FakeDriveWatcher:
    def __init__(self, changes_page: DriveChangesPage | None = None) -> None:
        self._changes_page = changes_page or DriveChangesPage(files=[], next_page_token="token-2")

    def get_start_page_token(self) -> str:
        return "start-token"

    def watch(
        self,
        channel_id: str,
        folder_id: str,
        webhook_url: str,
        token: str,
        start_page_token: str,
    ) -> DriveWatchRegistration:
        return DriveWatchRegistration(
            resource_id="resource-1", expires_at=datetime(2026, 1, 1, tzinfo=UTC)
        )

    def list_changes(self, page_token: str) -> DriveChangesPage:
        return self._changes_page


@pytest.fixture
def channels():
    return InMemoryDriveWatchChannelRepository()


@pytest.fixture
def documents():
    return InMemoryDocumentRepository()


@pytest.fixture
def process_use_case():
    return FakeProcessUploadedDocument()


@pytest.fixture
def drive_watcher():
    return FakeDriveWatcher()


@pytest.fixture
def subscribe_use_case(drive_watcher, channels):
    return SubscribeDriveWebhook(drive_watcher, channels)


@pytest.fixture
def process_notification_use_case(channels, drive_watcher, documents, process_use_case):
    return ProcessDriveChangeNotification(channels, drive_watcher, documents, process_use_case)


@pytest.fixture
def client(process_use_case, subscribe_use_case, process_notification_use_case, channels):
    app.dependency_overrides[deps.get_process_uploaded_document_use_case] = lambda: process_use_case
    app.dependency_overrides[deps.get_subscribe_drive_webhook_use_case] = lambda: subscribe_use_case
    app.dependency_overrides[deps.get_process_drive_change_notification_use_case] = lambda: (
        process_notification_use_case
    )
    app.dependency_overrides[deps.get_drive_watch_channel_repository] = lambda: channels
    app.dependency_overrides[require_session] = lambda: None

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _save_channel(channels, **overrides) -> DriveWatchChannel:
    defaults = {
        "id": "channel-1",
        "resource_id": "resource-1",
        "folder_id": "folder-1",
        "client_id": "client-1",
        "token": CHANNEL_TOKEN,
        "page_token": "token-1",
        "expires_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    channel = DriveWatchChannel(**{**defaults, **overrides})
    channels.save(channel)
    return channel


def test_drive_webhook_processes_the_channels_changes(
    client, channels, process_use_case, process_notification_use_case
):
    _save_channel(channels)
    client.app.dependency_overrides[deps.get_process_drive_change_notification_use_case] = lambda: (
        ProcessDriveChangeNotification(
            channels,
            FakeDriveWatcher(
                DriveChangesPage(
                    files=[
                        DriveChangedFile(
                            id="file-1",
                            name="invoice.pdf",
                            mime_type="application/pdf",
                            parents=["folder-1"],
                            trashed=False,
                        )
                    ],
                    next_page_token="token-2",
                )
            ),
            InMemoryDocumentRepository(),
            process_use_case,
        )
    )

    response = client.post(
        "/webhooks/drive",
        headers={
            "X-Goog-Channel-Token": CHANNEL_TOKEN,
            "X-Goog-Channel-Id": "channel-1",
            "X-Goog-Resource-State": "update",
        },
    )

    assert response.status_code == 200
    assert len(process_use_case.calls) == 1
    assert process_use_case.calls[0].drive_file_id == "file-1"


def test_drive_webhook_rejects_a_missing_token(client, channels):
    _save_channel(channels)

    response = client.post("/webhooks/drive", headers={"X-Goog-Channel-Id": "channel-1"})

    assert response.status_code == 401


def test_drive_webhook_rejects_a_mismatched_token(client, channels):
    _save_channel(channels)

    response = client.post(
        "/webhooks/drive",
        headers={"X-Goog-Channel-Token": "wrong-secret", "X-Goog-Channel-Id": "channel-1"},
    )

    assert response.status_code == 401


def test_drive_webhook_rejects_an_unknown_channel(client):
    response = client.post(
        "/webhooks/drive",
        headers={"X-Goog-Channel-Token": "anything", "X-Goog-Channel-Id": "unknown"},
    )

    assert response.status_code == 401


def test_drive_webhook_rejects_a_missing_channel_id(client):
    response = client.post("/webhooks/drive", headers={"X-Goog-Channel-Token": "anything"})

    assert response.status_code == 400


def test_subscribe_drive_webhook_registers_a_channel(client):
    response = client.post(
        "/webhooks/drive/subscribe", params={"folder_id": "folder-1", "client_id": "client-1"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["folder_id"] == "folder-1"
    assert body["client_id"] == "client-1"
    # The channel's shared secret must never be handed back over the API.
    assert "token" not in body


def test_subscribe_drive_webhook_requires_a_session():
    app.dependency_overrides.clear()

    with TestClient(app) as test_client:
        response = test_client.post(
            "/webhooks/drive/subscribe", params={"folder_id": "folder-1", "client_id": "client-1"}
        )

    assert response.status_code == 401
