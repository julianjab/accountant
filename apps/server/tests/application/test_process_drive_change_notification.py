from datetime import UTC, datetime

from server.application.use_cases import (
    ProcessDriveChangeNotification,
    ProcessUploadedDocumentInput,
)
from server.domain.entities import (
    Document,
    DocumentStatus,
    DriveChangedFile,
    DriveChangesPage,
    DriveWatchChannel,
)

_CHANNEL = DriveWatchChannel(
    id="channel-1",
    resource_id="resource-1",
    folder_id="folder-1",
    client_id="client-1",
    token="channel-secret",
    page_token="token-1",
    expires_at=datetime(2026, 1, 1, tzinfo=UTC),
)


class FakeDriveWatchChannelRepository:
    def __init__(self, channel: DriveWatchChannel | None) -> None:
        self._channel = channel
        self.saved: list[DriveWatchChannel] = []

    def save(self, channel: DriveWatchChannel) -> None:
        self._channel = channel
        self.saved.append(channel)

    def get_by_channel_id(self, channel_id: str) -> DriveWatchChannel | None:
        if self._channel is not None and self._channel.id == channel_id:
            return self._channel
        return None


class FakeDriveChangeReader:
    def __init__(self, page: DriveChangesPage) -> None:
        self._page = page
        self.list_changes_calls: list[str] = []

    def list_changes(self, page_token: str) -> DriveChangesPage:
        self.list_changes_calls.append(page_token)
        return self._page


class FakeDriveFileClaimRepository:
    def __init__(self, already_claimed: set[str] | None = None) -> None:
        self._claimed = set(already_claimed or set())

    def try_claim(self, drive_file_id: str) -> bool:
        if drive_file_id in self._claimed:
            return False
        self._claimed.add(drive_file_id)
        return True


class FakeProcessUploadedDocument:
    def __init__(self, fail_for: set[str] | None = None) -> None:
        self.calls: list[ProcessUploadedDocumentInput] = []
        self._fail_for = fail_for or set()

    def execute(self, data: ProcessUploadedDocumentInput) -> Document:
        self.calls.append(data)
        if data.drive_file_id in self._fail_for:
            raise RuntimeError("permanently broken download")
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


def _use_case(
    channels: FakeDriveWatchChannelRepository,
    change_reader: FakeDriveChangeReader,
    process_document: FakeProcessUploadedDocument,
    claims: FakeDriveFileClaimRepository | None = None,
) -> ProcessDriveChangeNotification:
    return ProcessDriveChangeNotification(
        channels, change_reader, claims or FakeDriveFileClaimRepository(), process_document
    )


def test_sync_notification_is_ignored():
    channels = FakeDriveWatchChannelRepository(_CHANNEL)
    change_reader = FakeDriveChangeReader(DriveChangesPage(files=[], next_page_token="token-2"))
    process_document = FakeProcessUploadedDocument()
    use_case = _use_case(channels, change_reader, process_document)

    processed = use_case.execute(channel_id="channel-1", resource_state="sync")

    assert processed == []
    assert change_reader.list_changes_calls == []
    assert process_document.calls == []


def test_unknown_channel_is_ignored():
    channels = FakeDriveWatchChannelRepository(None)
    change_reader = FakeDriveChangeReader(DriveChangesPage(files=[], next_page_token="token-2"))
    process_document = FakeProcessUploadedDocument()
    use_case = _use_case(channels, change_reader, process_document)

    processed = use_case.execute(channel_id="unknown", resource_state="update")

    assert processed == []
    assert change_reader.list_changes_calls == []
    assert process_document.calls == []


def test_processes_only_files_that_belong_to_the_watched_folder_and_are_not_trashed():
    channels = FakeDriveWatchChannelRepository(_CHANNEL)
    change_reader = FakeDriveChangeReader(
        DriveChangesPage(
            files=[
                DriveChangedFile(
                    id="file-1",
                    name="invoice.pdf",
                    mime_type="application/pdf",
                    parents=["folder-1"],
                    trashed=False,
                ),
                DriveChangedFile(
                    id="file-2",
                    name="deleted.pdf",
                    mime_type="application/pdf",
                    parents=["folder-1"],
                    trashed=True,
                ),
                DriveChangedFile(
                    id="file-3",
                    name="other-folder.pdf",
                    mime_type="application/pdf",
                    parents=["other-folder"],
                    trashed=False,
                ),
            ],
            next_page_token="token-2",
        )
    )
    process_document = FakeProcessUploadedDocument()
    use_case = _use_case(channels, change_reader, process_document)

    processed = use_case.execute(channel_id="channel-1", resource_state="update")

    assert [d.drive_file_id for d in processed] == ["file-1"]
    [call] = process_document.calls
    assert call.client_id == "client-1"
    assert call.drive_file_id == "file-1"
    assert call.file_reference == "file-1"

    assert change_reader.list_changes_calls == ["token-1"]
    assert channels.saved[-1].page_token == "token-2"


def test_skips_native_google_types_that_cannot_be_downloaded():
    channels = FakeDriveWatchChannelRepository(_CHANNEL)
    change_reader = FakeDriveChangeReader(
        DriveChangesPage(
            files=[
                DriveChangedFile(
                    id="folder-2",
                    name="subfolder",
                    mime_type="application/vnd.google-apps.folder",
                    parents=["folder-1"],
                    trashed=False,
                ),
                DriveChangedFile(
                    id="doc-1",
                    name="native doc",
                    mime_type="application/vnd.google-apps.document",
                    parents=["folder-1"],
                    trashed=False,
                ),
            ],
            next_page_token="token-2",
        )
    )
    process_document = FakeProcessUploadedDocument()
    use_case = _use_case(channels, change_reader, process_document)

    processed = use_case.execute(channel_id="channel-1", resource_state="update")

    assert processed == []
    assert process_document.calls == []


def test_skips_a_file_that_was_already_claimed():
    channels = FakeDriveWatchChannelRepository(_CHANNEL)
    change_reader = FakeDriveChangeReader(
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
    )
    process_document = FakeProcessUploadedDocument()
    claims = FakeDriveFileClaimRepository(already_claimed={"file-1"})
    use_case = _use_case(channels, change_reader, process_document, claims)

    processed = use_case.execute(channel_id="channel-1", resource_state="update")

    # Drive notifications are at-least-once: a retry must not duplicate the document.
    assert processed == []
    assert process_document.calls == []
    assert channels.saved[-1].page_token == "token-2"


def test_a_permanently_failing_file_does_not_wedge_the_cursor():
    channels = FakeDriveWatchChannelRepository(_CHANNEL)
    change_reader = FakeDriveChangeReader(
        DriveChangesPage(
            files=[
                DriveChangedFile(
                    id="file-1",
                    name="broken.pdf",
                    mime_type="application/pdf",
                    parents=["folder-1"],
                    trashed=False,
                ),
                DriveChangedFile(
                    id="file-2",
                    name="ok.pdf",
                    mime_type="application/pdf",
                    parents=["folder-1"],
                    trashed=False,
                ),
            ],
            next_page_token="token-2",
        )
    )
    process_document = FakeProcessUploadedDocument(fail_for={"file-1"})
    use_case = _use_case(channels, change_reader, process_document)

    processed = use_case.execute(channel_id="channel-1", resource_state="update")

    # file-1 failed but must not stop file-2 from being processed, and the
    # cursor still advances so this channel is not stuck on this page forever.
    assert [d.drive_file_id for d in processed] == ["file-2"]
    assert channels.saved[-1].page_token == "token-2"
