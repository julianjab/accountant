import threading

from server.domain.entities import (
    Client,
    Document,
    DocumentStatus,
    DocumentType,
    DriveWatchChannel,
    ExtractedData,
    GoogleSession,
)


class InMemoryClientRepository:
    def __init__(self) -> None:
        self._items: dict[str, Client] = {}

    def save(self, client: Client) -> None:
        self._items[client.id] = client

    def get(self, client_id: str) -> Client | None:
        return self._items.get(client_id)

    def list_all(self) -> list[Client]:
        return list(self._items.values())


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self._items: dict[str, Document] = {}

    def save(self, document: Document) -> None:
        self._items[document.id] = document

    def get(self, document_id: str) -> Document | None:
        return self._items.get(document_id)

    def list_by_client(self, client_id: str) -> list[Document]:
        return [d for d in self._items.values() if d.client_id == client_id]

    def list_all(self, status: DocumentStatus | None = None) -> list[Document]:
        if status is None:
            return list(self._items.values())
        return [d for d in self._items.values() if d.status == status]

    def get_by_drive_file_id_and_client(
        self, drive_file_id: str, client_id: str
    ) -> Document | None:
        return next(
            (
                d
                for d in self._items.values()
                if d.drive_file_id == drive_file_id and d.client_id == client_id
            ),
            None,
        )


class InMemoryDocumentTypeRepository:
    def __init__(self) -> None:
        self._items: dict[str, DocumentType] = {}

    def save(self, document_type: DocumentType) -> None:
        self._items[document_type.id] = document_type

    def get(self, document_type_id: str) -> DocumentType | None:
        return self._items.get(document_type_id)

    def list_active(self) -> list[DocumentType]:
        return [t for t in self._items.values() if t.active]

    def list_all(self) -> list[DocumentType]:
        return list(self._items.values())


class InMemoryExtractedDataRepository:
    def __init__(self) -> None:
        self._items: dict[str, ExtractedData] = {}

    def save(self, extracted_data: ExtractedData) -> None:
        self._items[extracted_data.document_id] = extracted_data

    def get_by_document(self, document_id: str) -> ExtractedData | None:
        return self._items.get(document_id)


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._items: dict[str, GoogleSession] = {}

    def save(self, session: GoogleSession) -> None:
        self._items[session.id] = session

    def get(self, session_id: str) -> GoogleSession | None:
        return self._items.get(session_id)

    def delete(self, session_id: str) -> None:
        self._items.pop(session_id, None)

    def delete_for_user(self, email: str) -> None:
        for session_id in [k for k, v in self._items.items() if v.user.email == email]:
            del self._items[session_id]


class InMemoryDriveWatchChannelRepository:
    def __init__(self) -> None:
        self._items: dict[str, DriveWatchChannel] = {}

    def save(self, channel: DriveWatchChannel) -> None:
        self._items[channel.id] = channel

    def get_by_channel_id(self, channel_id: str) -> DriveWatchChannel | None:
        return self._items.get(channel_id)


class InMemoryDriveFileClaimRepository:
    """Dev-only fallback. Sync FastAPI route handlers (including the ones a
    BackgroundTasks callback runs from) execute in the threadpool, not the
    event loop, so a plain check-then-add on a set is not atomic; a lock makes
    it so within this single process."""

    def __init__(self) -> None:
        self._claimed: set[str] = set()
        self._failures: dict[str, int] = {}
        self._lock = threading.Lock()

    def try_claim(self, key: str) -> bool:
        with self._lock:
            if key in self._claimed:
                return False
            self._claimed.add(key)
            return True

    def release(self, key: str) -> None:
        with self._lock:
            self._claimed.discard(key)

    def record_failure(self, key: str) -> int:
        with self._lock:
            self._failures[key] = self._failures.get(key, 0) + 1
            return self._failures[key]

    def clear_failures(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
