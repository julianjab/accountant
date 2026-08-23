import logging
from dataclasses import replace

from server.application.use_cases.process_uploaded_document import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
)
from server.domain.entities import Document, DocumentStatus, DriveChangedFile, DriveWatchChannel
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

# A file that fails this many times in a row (e.g. a permanently unsupported
# type, revoked access) stops being retried: without a cap, a poison-pill file
# would make every future notification re-list and re-attempt the same window
# forever, at ever-growing cost against the Drive and OCR APIs.
_MAX_ATTEMPTS = 3


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
            # A document already PROCESSED for this channel's client is the
            # only thing that should block a retry: ProcessUploadedDocument
            # always creates a fresh Document id rather than resuming one, so
            # retrying past a real success would duplicate it. A FAILED (or
            # missing) document for this file/client is exactly what should be
            # retried; a document another channel/client already has for the
            # same Drive file id does not count, since claims are per-channel.
            existing = self._documents.get_by_drive_file_id_and_client(file.id, channel.client_id)
            if existing is not None and existing.status == DocumentStatus.PROCESSED:
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

            document = self._attempt(channel, file)
            if document is None:
                had_failures = True
                continue
            processed.append(document)
            if document.status == DocumentStatus.PROCESSED:
                self._claims.clear_failures(claim_key)

        return processed, had_failures

    def _attempt(self, channel: DriveWatchChannel, file: DriveChangedFile) -> Document | None:
        """Runs one processing attempt.

        Returns the resulting Document, or None if the caller should retry
        this file on a future notification instead of treating it as done.
        """
        claim_key = f"{channel.id}:{file.id}"
        try:
            document = self._process_document.execute(
                ProcessUploadedDocumentInput(
                    client_id=channel.client_id,
                    drive_file_id=file.id,
                    file_reference=file.id,
                )
            )
        except Exception:
            # Only storage.download can still raise here: nothing was
            # persisted, so this attempt is a clean, safe-to-retry no-op.
            logger.exception("Failed to download Drive file %s for channel %s", file.id, channel.id)
            self._should_retry(claim_key, file.id, channel.id)
            return None

        if document.status != DocumentStatus.FAILED:
            return document

        logger.warning(
            "Drive file %s for channel %s failed to process: %s",
            file.id,
            channel.id,
            document.error,
        )
        if self._should_retry(claim_key, file.id, channel.id):
            return None
        # Gave up: keep the FAILED document as the visible, inspectable
        # record of what happened, rather than discarding it silently.
        return document

    def _should_retry(self, claim_key: str, file_id: str, channel_id: str) -> bool:
        attempts = self._claims.record_failure(claim_key)
        if attempts < _MAX_ATTEMPTS:
            self._claims.release(claim_key)
            return True
        logger.error(
            "Giving up on Drive file %s for channel %s after %d attempts",
            file_id,
            channel_id,
            attempts,
        )
        return False

    @staticmethod
    def _should_process(folder_id: str, file: DriveChangedFile) -> bool:
        return (
            not file.trashed
            and folder_id in file.parents
            and not file.mime_type.startswith(_NATIVE_GOOGLE_MIME_PREFIX)
        )
