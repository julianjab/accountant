import logging
import threading
import uuid
from dataclasses import replace
from datetime import UTC, datetime

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
        # Drive can deliver more than one notification for the same channel
        # concurrently, and BackgroundTasks callbacks run on FastAPI's
        # threadpool. Without serializing per channel, two handlers could both
        # read the same page_token, one could advance the cursor past a file
        # the other is still (and later fails) processing, permanently losing
        # it. This only guards a single process; a multi-instance deployment
        # would need a distributed lock instead.
        self._channel_locks: dict[str, threading.Lock] = {}
        self._channel_locks_guard = threading.Lock()

    def execute(self, channel_id: str, resource_state: str) -> list[Document]:
        if resource_state == _SYNC_RESOURCE_STATE:
            return []

        with self._lock_for(channel_id):
            channel = self._channels.get_by_channel_id(channel_id)
            if channel is None:
                return []

            page = self._change_reader.list_changes(channel.page_token)
            processed, had_failures = self._process_page(channel, page.files)

            # Only move the cursor past a page that fully succeeded. Drive
            # never re-notifies for a change it already reported, so
            # advancing past a failure would make that file unprocessable
            # forever; leaving the cursor in place means the next
            # notification (for any reason) simply re-lists the same window
            # and retries it, while claims already held by files that did
            # succeed keep them from being duplicated.
            if not had_failures:
                self._channels.save(replace(channel, page_token=page.next_page_token))
            return processed

    def _lock_for(self, channel_id: str) -> threading.Lock:
        with self._channel_locks_guard:
            return self._channel_locks.setdefault(channel_id, threading.Lock())

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

            document, needs_retry = self._attempt(channel, file)
            if needs_retry:
                had_failures = True
                continue
            if document is not None:
                processed.append(document)
                if document.status == DocumentStatus.PROCESSED:
                    self._claims.clear_failures(claim_key)

        return processed, had_failures

    def _attempt(
        self, channel: DriveWatchChannel, file: DriveChangedFile
    ) -> tuple[Document | None, bool]:
        """Runs one processing attempt.

        Returns the resulting Document (None if nothing could be persisted,
        e.g. the download itself failed) and whether the caller should treat
        this file as still needing a retry on a future notification. A False
        here means "done with this file for now", whether that is a genuine
        success or giving up on it after too many failures — either way the
        channel's cursor must be free to move on.
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
        except Exception as exc:
            # Only storage.download can still raise here: nothing was
            # persisted, so this attempt is a clean, safe-to-retry no-op.
            logger.exception("Failed to download Drive file %s for channel %s", file.id, channel.id)
            if self._should_retry(claim_key, file.id, channel.id):
                return None, True
            # Giving up with nothing persisted would leave this file with no
            # record at all besides a log line; persist a terminal FAILED
            # document directly (ProcessUploadedDocument never got the
            # chance to) so it stays inspectable like every other outcome.
            return self._give_up_document(channel, file, str(exc)), False

        if document.status != DocumentStatus.FAILED:
            return document, False

        logger.warning(
            "Drive file %s for channel %s failed to process: %s",
            file.id,
            channel.id,
            document.error,
        )
        needs_retry = self._should_retry(claim_key, file.id, channel.id)
        # Keep the FAILED document either way: whether it will be retried or
        # this was the last attempt, it is the visible, inspectable record of
        # what happened, instead of being discarded silently.
        return document, needs_retry

    def _give_up_document(
        self, channel: DriveWatchChannel, file: DriveChangedFile, error: str
    ) -> Document:
        # Reuse the row an earlier attempt (e.g. one that got past download
        # and failed classify/OCR instead) may have already left behind,
        # exactly like ProcessUploadedDocument does: otherwise this file
        # would end up with two FAILED rows instead of one.
        existing = self._documents.get_by_drive_file_id_and_client(file.id, channel.client_id)
        document_id = (
            existing.id
            if existing is not None and existing.status != DocumentStatus.PROCESSED
            else str(uuid.uuid4())
        )
        document = Document(
            id=document_id,
            client_id=channel.client_id,
            document_type_id=None,
            drive_file_id=file.id,
            file_name=file.name,
            mime_type=file.mime_type,
            status=DocumentStatus.FAILED,
            error=error,
            created_at=datetime.now(UTC),
        )
        self._documents.save(document)
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
