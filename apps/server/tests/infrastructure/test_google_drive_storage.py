from datetime import UTC, datetime

from server.infrastructure.adapters import google_drive_storage
from server.infrastructure.adapters.google_drive_storage import (
    GoogleDriveStorage,
    GoogleDriveWatcher,
)


class FakeCredentials:
    pass


class FakeRequest:
    def __init__(self, result: dict) -> None:
        self._result = result

    def execute(self) -> dict:
        return self._result


class FakeFiles:
    def __init__(self, get_result: dict) -> None:
        self._get_result = get_result

    def get(self, **kwargs: object) -> FakeRequest:
        return FakeRequest(self._get_result)

    def get_media(self, **kwargs: object) -> object:
        return object()


class FakeChanges:
    def __init__(
        self, start_page_token_result: dict, watch_result: dict, list_results: list[dict]
    ) -> None:
        self._start_page_token_result = start_page_token_result
        self._watch_result = watch_result
        self._list_results = list(list_results)
        self.watch_calls: list[dict] = []
        self.list_calls: list[dict] = []

    def getStartPageToken(self, **kwargs: object) -> FakeRequest:  # noqa: N802 - matches the Drive API
        return FakeRequest(self._start_page_token_result)

    def watch(self, **kwargs: object) -> FakeRequest:
        self.watch_calls.append(dict(kwargs))
        return FakeRequest(self._watch_result)

    def list(self, **kwargs: object) -> FakeRequest:
        self.list_calls.append(dict(kwargs))
        return FakeRequest(self._list_results[len(self.list_calls) - 1])


class FakeDriveClient:
    def __init__(
        self,
        get_result: dict | None = None,
        start_page_token_result: dict | None = None,
        watch_result: dict | None = None,
        list_results: list[dict] | None = None,
    ) -> None:
        self.files_obj = FakeFiles(get_result or {})
        self.changes_obj = FakeChanges(
            start_page_token_result or {}, watch_result or {}, list_results or []
        )

    def files(self) -> FakeFiles:
        return self.files_obj

    def changes(self) -> FakeChanges:
        return self.changes_obj


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


def test_get_start_page_token_returns_the_cursor(monkeypatch):
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(start_page_token_result={"startPageToken": "token-1"})
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    watcher = GoogleDriveWatcher("service-account.json")

    assert watcher.get_start_page_token() == "token-1"


def test_watch_registers_a_web_hook_channel_via_the_changes_api(monkeypatch):
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(
        watch_result={
            "resourceId": "resource-1",
            "expiration": "1735689600000",  # 2025-01-01T00:00:00Z in epoch millis
        }
    )
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    watcher = GoogleDriveWatcher("service-account.json")
    registration = watcher.watch(
        channel_id="channel-1",
        folder_id="folder-1",
        webhook_url="https://example.com/webhooks/drive",
        token="secret-token",
        start_page_token="token-1",
    )

    [call] = fake_client.changes_obj.watch_calls
    assert call["pageToken"] == "token-1"
    assert call["body"]["id"] == "channel-1"
    assert call["body"]["type"] == "web_hook"
    assert call["body"]["address"] == "https://example.com/webhooks/drive"
    assert call["body"]["token"] == "secret-token"

    assert registration.resource_id == "resource-1"
    assert registration.expires_at == datetime(2025, 1, 1, tzinfo=UTC)


def test_watch_defaults_the_expiration_when_drive_omits_it(monkeypatch):
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(watch_result={"resourceId": "resource-1"})
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    before = datetime.now(UTC)
    watcher = GoogleDriveWatcher("service-account.json")
    registration = watcher.watch("channel-1", "folder-1", "https://example.com", "token", "token-1")

    assert registration.expires_at > before


def test_list_changes_skips_removed_and_missing_files(monkeypatch):
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(
        list_results=[
            {
                "newStartPageToken": "token-2",
                "changes": [
                    {
                        "fileId": "file-1",
                        "removed": False,
                        "file": {
                            "name": "invoice.pdf",
                            "mimeType": "application/pdf",
                            "parents": ["folder-1"],
                            "trashed": False,
                        },
                    },
                    {"fileId": "file-2", "removed": True},
                    {"fileId": "file-3", "removed": False},
                ],
            }
        ]
    )
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    watcher = GoogleDriveWatcher("service-account.json")
    page = watcher.list_changes("token-1")

    [call] = fake_client.changes_obj.list_calls
    assert call["pageToken"] == "token-1"

    assert len(page.files) == 1
    assert page.files[0].id == "file-1"
    assert page.files[0].name == "invoice.pdf"
    assert page.files[0].mime_type == "application/pdf"
    assert page.files[0].parents == ["folder-1"]
    assert page.files[0].trashed is False
    assert page.next_page_token == "token-2"


def test_list_changes_follows_pagination_until_the_new_start_page_token(monkeypatch):
    # A single call returning only "nextPageToken" would silently drop every
    # change past the first page; the adapter must keep paging until Drive
    # hands back "newStartPageToken", the cursor that is safe to persist.
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(
        list_results=[
            {
                "nextPageToken": "token-2",
                "changes": [
                    {
                        "fileId": "file-1",
                        "removed": False,
                        "file": {
                            "name": "a.pdf",
                            "mimeType": "application/pdf",
                            "parents": ["folder-1"],
                            "trashed": False,
                        },
                    }
                ],
            },
            {
                "newStartPageToken": "token-final",
                "changes": [
                    {
                        "fileId": "file-2",
                        "removed": False,
                        "file": {
                            "name": "b.pdf",
                            "mimeType": "application/pdf",
                            "parents": ["folder-1"],
                            "trashed": False,
                        },
                    }
                ],
            },
        ]
    )
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    watcher = GoogleDriveWatcher("service-account.json")
    page = watcher.list_changes("token-1")

    assert [call["pageToken"] for call in fake_client.changes_obj.list_calls] == [
        "token-1",
        "token-2",
    ]
    assert [f.id for f in page.files] == ["file-1", "file-2"]
    assert page.next_page_token == "token-final"


def test_list_changes_falls_back_to_the_new_start_page_token_on_the_last_page(monkeypatch):
    patch_credentials(monkeypatch)
    fake_client = FakeDriveClient(
        list_results=[{"newStartPageToken": "token-final", "changes": []}]
    )
    monkeypatch.setattr(google_drive_storage, "build", lambda *a, **k: fake_client)

    watcher = GoogleDriveWatcher("service-account.json")
    page = watcher.list_changes("token-1")

    assert page.files == []
    assert page.next_page_token == "token-final"


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
