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


class DocumentTypeRepository(Protocol):
    def save(self, document_type: DocumentType) -> None: ...
    def get(self, document_type_id: str) -> DocumentType | None: ...
    def list_active(self) -> list[DocumentType]: ...
    def list_all(self) -> list[DocumentType]: ...


class ExtractedDataRepository(Protocol):
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


class DriveFileClaimRepository(Protocol):
    def try_claim(self, drive_file_id: str) -> bool:
        """Atomically marks a Drive file as being processed.

        Returns True the first time it is called for a given ``drive_file_id``
        and False on every call after, including concurrent ones. This is what
        makes at-least-once Drive notifications safe to process without
        creating duplicate documents.
        """
        ...

    def release(self, drive_file_id: str) -> None:
        """Undoes a claim after a failed processing attempt.

        Without this, a file that fails for a transient reason (a timed-out
        AI call, Drive/Firestore briefly unavailable, ...) would stay claimed
        forever: Drive never re-notifies for a change it already reported, so
        that file would silently never be processed again.
        """
        ...
