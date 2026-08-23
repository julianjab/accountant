import logging
from dataclasses import replace

from server.application.use_cases.process_uploaded_document import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
)
from server.domain.entities import Document, DriveChangedFile, DriveWatchChannel
from server.domain.ports import (
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
        process_document: ProcessUploadedDocument,
    ) -> None:
        self._channels = channels
        self._change_reader = change_reader
        self._claims = claims
        self._process_document = process_document

    def execute(self, channel_id: str, resource_state: str) -> list[Document]:
        if resource_state == _SYNC_RESOURCE_STATE:
            return []

        channel = self._channels.get_by_channel_id(channel_id)
        if channel is None:
            return []

        page = self._change_reader.list_changes(channel.page_token)

        # The cursor advances once the whole page has been attempted, win or
        # lose: a file that fails permanently (revoked access, corrupt upload,
        # ...) must not wedge this channel on the same page_token forever, since
        # Drive never re-notifies for changes it already reported.
        try:
            processed = self._process_page(channel, page.files)
        finally:
            self._channels.save(replace(channel, page_token=page.next_page_token))
        return processed

    def _process_page(
        self, channel: DriveWatchChannel, files: list[DriveChangedFile]
    ) -> list[Document]:
        processed = []
        for file in files:
            if not self._should_process(channel.folder_id, file):
                continue
            # Drive notifications are at-least-once, so the same file can be
            # handed back on retry; the claim is what makes that safe to skip
            # instead of racing another in-flight handler into a duplicate.
            if not self._claims.try_claim(file.id):
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
                # Undo the claim so this file is eligible again: Drive never
                # re-notifies for a change it already reported, so a claim left
                # in place after a failure would make the file unprocessable
                # forever instead of just until the next retry picks it up.
                self._claims.release(file.id)
        return processed

    @staticmethod
    def _should_process(folder_id: str, file: DriveChangedFile) -> bool:
        return (
            not file.trashed
            and folder_id in file.parents
            and not file.mime_type.startswith(_NATIVE_GOOGLE_MIME_PREFIX)
        )
