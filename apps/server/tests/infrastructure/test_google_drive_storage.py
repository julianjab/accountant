from datetime import UTC, datetime

from server.infrastructure.adapters import google_drive_storage
from server.infrastructure.adapters.google_drive_storage import (
    GoogleDriveStorage,
    GoogleDriveWatcher,
)


class FakeCredentials:
    pass


class FakeFilesRequest:
    def __init__(self, result: dict) -> None:
        self._result = result

    def execute(self) -> dict:
        return self._result


class FakeFiles:
    def __init__(self, get_result: dict, watch_result: dict) -> None:
        self._get_result = get_result
        self._watch_result = watch_result
        self.watch_calls: list[dict] = []

    def get(self, **kwargs: object) -> FakeFilesRequest:
        return FakeFilesRequest(self._get_result)

    def get_media(self, **kwargs: object) -> object:
        return object()

    def watch(self, **kwargs: object) -> FakeFilesRequest:
        self.watch_calls.append(dict(kwargs))
        return FakeFilesRequest(self._watch_result)


class FakeDriveClient:
    def __init__(self, get_result: dict | None = None, watch_result: dict | None = None) -> None:
        self.files_obj = FakeFiles(get_result or {}, watch_result or {})

    def files(self) -> FakeFiles:
        return self.files_obj


def patch_credentials(monkeypatch):
    captured = {}

    def fake_from_service_account_file(filename, scopes):
        captured["filename"] = filename
        captured["scopes"] = scopes
        return FakeCredentials()

    monkeypatch.setattr(
        google_drive_storage.service_account.Credentials,
        "from_service_account_file",
        staticmethod(fake_from_service_account_file),
    )
    return captured


def test_build_drive_client_uses_the_service_account_file_and_readonly_scope(monkeypatch):
    captured = patch_credentials(monkeypatch)
    build_calls = {}

    def fake_build(service_name, version, credentials):
        build_calls["service_name"] = service_name
        build_calls["version"] = version
        build_calls["credentials"] = credentials
        return FakeDriveClient()

    monkeypatch.setattr(google_drive_storage, "build", fake_build)

    google_drive_storage._build_drive_client("service-account.json")

    assert captured["filename"] == "service-account.json"
    assert captured["scopes"] == ["https://www.googleapis.com/auth/drive.readonly"]
    assert build_calls["service_name"] == "drive"
    assert build_calls["version"] == "v3"
    assert isinstance(build_calls["credentials"], FakeCredentials)


def test_google_drive_watcher_registers_a_web_hook_channel(monkeypatch):
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(
        watch_result={
            "resourceId": "resource-1",
            "expiration": "1735689600000",  # 2025-01-01T00:00:00Z in epoch millis
        }
    )
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    watcher = GoogleDriveWatcher("service-account.json")
    channel = watcher.watch(
        folder_id="folder-1",
        webhook_url="https://example.com/webhooks/drive",
        token="secret-token",
    )

    [call] = fake_client.files_obj.watch_calls
    assert call["fileId"] == "folder-1"
    assert call["body"]["type"] == "web_hook"
    assert call["body"]["address"] == "https://example.com/webhooks/drive"
    assert call["body"]["token"] == "secret-token"
    assert call["body"]["id"]  # a channel id was generated

    assert channel.folder_id == "folder-1"
    assert channel.resource_id == "resource-1"
    assert channel.id == call["body"]["id"]
    assert channel.expires_at == datetime(2025, 1, 1, tzinfo=UTC)


def test_google_drive_watcher_generates_a_unique_channel_id_per_call(monkeypatch):
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(
        watch_result={"resourceId": "resource-1", "expiration": "1735689600000"}
    )
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    watcher = GoogleDriveWatcher("service-account.json")
    first = watcher.watch("folder-1", "https://example.com/webhooks/drive", "token")
    second = watcher.watch("folder-1", "https://example.com/webhooks/drive", "token")

    assert first.id != second.id


def test_google_drive_storage_downloads_a_file(monkeypatch):
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(get_result={"name": "invoice.pdf", "mimeType": "application/pdf"})
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    class FakeDownloader:
        def __init__(self, buffer, request) -> None:
            self._buffer = buffer

        def next_chunk(self):
            self._buffer.write(b"file-bytes")
            return None, True

    monkeypatch.setattr(google_drive_storage, "MediaIoBaseDownload", FakeDownloader)

    storage = GoogleDriveStorage("service-account.json")
    content = storage.download("file-1")

    assert content.data == b"file-bytes"
    assert content.mime_type == "application/pdf"
    assert content.file_name == "invoice.pdf"
