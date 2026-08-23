from dataclasses import replace

from server.application.use_cases.process_uploaded_document import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
)
from server.domain.entities import Document
from server.domain.ports import DriveChangeReader, DriveWatchChannelRepository

# Drive's initial handshake notification when a channel is created: no changes yet.
_SYNC_RESOURCE_STATE = "sync"


class ProcessDriveChangeNotification:
    """Triggered by a Drive push notification: enumerates what actually changed
    since the channel's last cursor and processes every new file in its folder."""

    def __init__(
        self,
        channels: DriveWatchChannelRepository,
        change_reader: DriveChangeReader,
        process_document: ProcessUploadedDocument,
    ) -> None:
        self._channels = channels
        self._change_reader = change_reader
        self._process_document = process_document

    def execute(self, channel_id: str, resource_state: str) -> list[Document]:
        if resource_state == _SYNC_RESOURCE_STATE:
            return []

        channel = self._channels.get_by_channel_id(channel_id)
        if channel is None:
            return []

        page = self._change_reader.list_changes(channel.page_token)

        processed = []
        for file in page.files:
            if not file.trashed and channel.folder_id in file.parents:
                processed.append(
                    self._process_document.execute(
                        ProcessUploadedDocumentInput(
                            client_id=channel.client_id,
                            drive_file_id=file.id,
                            file_reference=file.id,
                        )
                    )
                )

        self._channels.save(replace(channel, page_token=page.next_page_token))
        return processed
