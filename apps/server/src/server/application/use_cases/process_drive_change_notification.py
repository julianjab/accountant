import logging
from dataclasses import replace

from server.application.use_cases.process_uploaded_document import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
)
from server.domain.entities import Document, DriveChangedFile, DriveWatchChannel
from server.domain.ports import (
    DocumentRepository,
    DriveChangeReader,
    DriveFileClaimRepository,
    DriveWatchChannelRepository,
)

logger = logging.getLogger(__name__)

# Drive's initial handshake notification when a channel is created: no changes yet.
_SYNC_RESOURCE_STATE = "sync"

# Native Google types (Docs, Sheets, folders, ...) cannot be fetched with a plain
# files().get_media() download the way a PDF/image can; they need an export.
# None of them are documents this pipeline can classify or OCR, so skip them.
_NATIVE_GOOGLE_MIME_PREFIX = "application/vnd.google-apps."


class ProcessDriveChangeNotification:
    """Triggered by a Drive push notification: enumerates what actually changed
    since the channel's last cursor and processes every new file in its folder."""

    def __init__(
        self,
        channels: DriveWatchChannelRepository,
        change_reader: DriveChangeReader,
        claims: DriveFileClaimRepository,
        documents: DocumentRepository,
        process_document: ProcessUploadedDocument,
    ) -> None:
        self._channels = channels
        self._change_reader = change_reader
        self._claims = claims
        self._documents = documents
        self._process_document = process_document

    def execute(self, channel_id: str, resource_state: str) -> list[Document]:
        if resource_state == _SYNC_RESOURCE_STATE:
            return []

        channel = self._channels.get_by_channel_id(channel_id)
        if channel is None:
            return []

        page = self._change_reader.list_changes(channel.page_token)
        processed, had_failures = self._process_page(channel, page.files)

        # Only move the cursor past a page that fully succeeded. Drive never
        # re-notifies for a change it already reported, so advancing past a
        # failure would make that file unprocessable forever; leaving the
        # cursor in place means the next notification (for any reason) simply
        # re-lists the same window and retries it, while claims already held
        # by files that did succeed keep them from being duplicated.
        if not had_failures:
            self._channels.save(replace(channel, page_token=page.next_page_token))
        return processed

    def _process_page(
        self, channel: DriveWatchChannel, files: list[DriveChangedFile]
    ) -> tuple[list[Document], bool]:
        processed = []
        had_failures = False
        for file in files:
            if not self._should_process(channel.folder_id, file):
                continue
            # Scoped to the channel: the same Drive file can sit under more than
            # one watched folder (e.g. shared with two different clients), and
            # each of those channels must still get to process it once.
            claim_key = f"{channel.id}:{file.id}"
            # Drive notifications are at-least-once, so the same file can be
            # handed back on retry; the claim is what makes that safe to skip
            # instead of racing another in-flight handler into a duplicate.
            if not self._claims.try_claim(claim_key):
                continue
            try:
                processed.append(
                    self._process_document.execute(
                        ProcessUploadedDocumentInput(
                            client_id=channel.client_id,
                            drive_file_id=file.id,
                            file_reference=file.id,
                        )
                    )
                )
            except Exception:
                logger.exception(
                    "Failed to process Drive file %s for channel %s", file.id, channel.id
                )
                had_failures = True
                # Only undo the claim if nothing was persisted for this file:
                # ProcessUploadedDocument always creates a fresh Document id
                # rather than resuming one, so releasing the claim after it
                # already wrote a partial (CLASSIFYING/RUNNING_OCR) row would
                # let a retry create a second Document for the same file.
                if self._documents.get_by_drive_file_id(file.id) is None:
                    self._claims.release(claim_key)
        return processed, had_failures

    @staticmethod
    def _should_process(folder_id: str, file: DriveChangedFile) -> bool:
        return (
            not file.trashed
            and folder_id in file.parents
            and not file.mime_type.startswith(_NATIVE_GOOGLE_MIME_PREFIX)
        )
