from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.application.use_cases import ProcessUploadedDocumentInput, SubscribeDriveWebhook
from server.domain.entities import Document, DocumentStatus, DriveWatchChannel
from server.infrastructure.api import deps
from server.main import app

WEBHOOK_SECRET = "shared-secret"


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


@pytest.fixture
def process_use_case():
    return FakeProcessUploadedDocument()


@pytest.fixture
def subscribe_use_case():
    return SubscribeDriveWebhook(FakeDriveWatcher())


class FakeDriveWatcher:
    def watch(self, folder_id: str, webhook_url: str, token: str) -> DriveWatchChannel:
        return DriveWatchChannel(
            id="channel-1",
            resource_id="resource-1",
            folder_id=folder_id,
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


@pytest.fixture
def client(process_use_case, subscribe_use_case):
    app.dependency_overrides[deps.get_process_uploaded_document_use_case] = lambda: process_use_case
    app.dependency_overrides[deps.get_subscribe_drive_webhook_use_case] = lambda: subscribe_use_case

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def configure_webhook_secret(monkeypatch, secret: str = WEBHOOK_SECRET):
    monkeypatch.setattr(deps.get_settings(), "google_drive_webhook_secret", secret)


def webhook_payload():
    return {"client_id": "client-1", "drive_file_id": "file-1", "file_reference": "file-1"}


def test_drive_webhook_accepts_a_matching_token(client, monkeypatch, process_use_case):
    configure_webhook_secret(monkeypatch)

    response = client.post(
        "/webhooks/drive",
        json=webhook_payload(),
        headers={"X-Goog-Channel-Token": WEBHOOK_SECRET},
    )

    assert response.status_code == 201
    assert response.json()["id"] == "doc-1"
    assert len(process_use_case.calls) == 1


def test_drive_webhook_rejects_a_missing_token(client, monkeypatch):
    configure_webhook_secret(monkeypatch)

    response = client.post("/webhooks/drive", json=webhook_payload())

    assert response.status_code == 401


def test_drive_webhook_rejects_a_mismatched_token(client, monkeypatch):
    configure_webhook_secret(monkeypatch)

    response = client.post(
        "/webhooks/drive",
        json=webhook_payload(),
        headers={"X-Goog-Channel-Token": "wrong-secret"},
    )

    assert response.status_code == 401


def test_drive_webhook_rejects_everything_when_no_secret_is_configured(client, monkeypatch):
    configure_webhook_secret(monkeypatch, secret="")

    response = client.post(
        "/webhooks/drive",
        json=webhook_payload(),
        headers={"X-Goog-Channel-Token": "anything"},
    )

    assert response.status_code == 401


def test_subscribe_drive_webhook_registers_a_channel(client, monkeypatch):
    configure_webhook_secret(monkeypatch)

    response = client.post("/webhooks/drive/subscribe", params={"folder_id": "folder-1"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "channel-1"
    assert body["folder_id"] == "folder-1"


def test_subscribe_drive_webhook_fails_when_no_secret_is_configured(client, monkeypatch):
    configure_webhook_secret(monkeypatch, secret="")

    response = client.post("/webhooks/drive/subscribe", params={"folder_id": "folder-1"})

    assert response.status_code == 500
