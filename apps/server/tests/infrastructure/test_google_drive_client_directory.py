import pytest
from googleapiclient.errors import HttpError

from server.infrastructure.adapters.google_drive_client_directory import (
    DriveDirectoryError,
    GoogleDriveClientDirectory,
)


class FakeFiles:
    def __init__(self, pages: list[dict], error: Exception | None = None) -> None:
        self._pages = pages
        self._error = error
        self.calls: list[dict] = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        page = self._pages[len(self.calls) - 1]

        class _Request:
            def execute(self) -> dict:
                return page

        return _Request()


def directory(pages, error=None, root="root-1"):
    obj = GoogleDriveClientDirectory.__new__(GoogleDriveClientDirectory)
    files = FakeFiles(pages, error)

    class _Drive:
        def files(self):
            return files

    obj._drive = _Drive()
    obj._root_folder_id = root
    return obj, files


def test_subfolders_become_client_folders():
    subject, _ = directory([{"files": [{"id": "f1", "name": "Acme SAS"}]}])

    folders = subject.list_client_folders()

    assert [(f.id, f.name) for f in folders] == [("f1", "Acme SAS")]


def test_shared_drives_are_included():
    subject, files = directory([{"files": []}])

    subject.list_client_folders()

    # Without these the call succeeds and silently returns nothing for a folder
    # that lives in a Shared Drive.
    assert files.calls[0]["supportsAllDrives"] is True
    assert files.calls[0]["includeItemsFromAllDrives"] is True


def test_only_folders_in_the_configured_parent_are_requested():
    subject, files = directory([{"files": []}], root="root-9")

    subject.list_client_folders()

    query = files.calls[0]["q"]
    assert "'root-9' in parents" in query
    assert "application/vnd.google-apps.folder" in query
    assert "trashed = false" in query


def test_every_page_is_followed():
    subject, files = directory(
        [
            {"files": [{"id": "f1", "name": "A"}], "nextPageToken": "t1"},
            {"files": [{"id": "f2", "name": "B"}]},
        ]
    )

    folders = subject.list_client_folders()

    assert [f.name for f in folders] == ["A", "B"]
    assert files.calls[1]["pageToken"] == "t1"


def test_an_unconfigured_folder_is_reported():
    subject, _ = directory([{"files": []}], root="")

    with pytest.raises(DriveDirectoryError):
        subject.list_client_folders()


def test_a_drive_error_is_wrapped():
    response = type("R", (), {"status": 404, "reason": "Not Found"})()
    subject, _ = directory([], error=HttpError(resp=response, content=b"{}", uri="https://drive"))

    with pytest.raises(DriveDirectoryError):
        subject.list_client_folders()
