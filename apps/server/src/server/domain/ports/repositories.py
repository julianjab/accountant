from datetime import timedelta
from typing import Protocol

from server.domain.entities import (
    Client,
    Document,
    DocumentStatus,
    DocumentType,
    DriveWatchChannel,
    ExtractedData,
    GoogleSession,
)


class ClientRepository(Protocol):
    def save(self, client: Client) -> None: ...
    def get(self, client_id: str) -> Client | None: ...
    def list_all(self) -> list[Client]: ...


class DocumentRepository(Protocol):
    def save(self, document: Document) -> None: ...
    def get(self, document_id: str) -> Document | None: ...
    def list_by_client(self, client_id: str) -> list[Document]: ...
    def list_all(self, status: DocumentStatus | None = None) -> list[Document]: ...
    def get_by_drive_file_id_and_client(
        self, drive_file_id: str, client_id: str
    ) -> Document | None: ...


class DocumentTypeRepository(Protocol):
    def save(self, document_type: DocumentType) -> None: ...
    def get(self, document_type_id: str) -> DocumentType | None: ...
    def list_active(self) -> list[DocumentType]: ...
    def list_all(self) -> list[DocumentType]: ...


class ExtractedDataRepository(Protocol):
    """A document has at most one extraction: the current one.

    `save` replaces whatever the document had before rather than adding to it.
    Re-running OCR over a document is how a bad extraction gets corrected, so
    keeping both would leave `get_by_document` picking between a stale result
    and a fresh one with nothing to distinguish them.
    """

    def save(self, extracted_data: ExtractedData) -> None: ...
    def get_by_document(self, document_id: str) -> ExtractedData | None: ...


class SessionRepository(Protocol):
    def save(self, session: GoogleSession) -> None: ...
    def get(self, session_id: str) -> GoogleSession | None: ...
    def delete(self, session_id: str) -> None: ...
    def delete_for_user(self, email: str) -> None: ...


class DriveWatchChannelRepository(Protocol):
    def save(self, channel: DriveWatchChannel) -> None: ...
    def get_by_channel_id(self, channel_id: str) -> DriveWatchChannel | None: ...


# A claim older than this is treated as abandoned (the process holding it
# crashed before releasing or otherwise deciding an outcome) and can be
# re-claimed. Comfortably longer than any real classify/OCR call, short
# enough that a crashed claim does not stay stuck for long.
CLAIM_STALE_AFTER = timedelta(minutes=10)


class DriveFileClaimRepository(Protocol):
    def try_claim(self, key: str) -> bool:
        """Atomically marks a claim key (typically ``f"{channel_id}:{drive_file_id}"``)
        as being processed.

        Returns True the first time it is called for a given key and False on
        every call after, including concurrent ones. This is what makes
        at-least-once Drive notifications safe to process without creating
        duplicate documents. Keying by channel (not just the raw Drive file
        id) is what lets the same file be processed once per watched folder
        when it is shared into more than one.
        """
        ...

    def release(self, key: str) -> None:
        """Undoes a claim after a failed processing attempt.

        Without this, a file that fails for a transient reason (a timed-out
        AI call, Drive/Firestore briefly unavailable, ...) would stay claimed
        forever: Drive never re-notifies for a change it already reported, so
        that file would silently never be processed again.
        """
        ...

    def record_failure(self, key: str) -> int:
        """Records a failed attempt for a key and returns the running count.

        Lets a caller cap retries: without a limit, a file that fails for a
        permanent reason (an unsupported type, revoked access, ...) would be
        re-attempted on every future notification for that channel, forever.

        # TODO: this counter has no expiry, so failures from unrelated,
        # long-past incidents keep counting towards today's retry cap.
        """
        ...

    def clear_failures(self, key: str) -> None:
        """Resets the failure count for a key after it is eventually processed.

        Without this, an old, unrelated run of failures years ago against a
        key that later succeeded (and could reasonably fail again for a new,
        unrelated reason) would count towards today's retry cap immediately.
        """
        ...
