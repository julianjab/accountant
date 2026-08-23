"""Firestore-backed implementations of the domain repository ports.

Mapping is written out per entity rather than derived from the dataclasses: the
document shape is a storage contract that outlives any refactor of the entity,
so it should change deliberately, not as a side effect.

Documents themselves stay in Google Drive (see ``GoogleDriveStorage``); what
lives here is only their metadata and the data extracted from them.
"""

from datetime import UTC, datetime
from typing import Any

from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore import Client as FirestoreClient

from server.domain.entities import (
    Client,
    Document,
    DocumentStatus,
    DocumentType,
    DriveWatchChannel,
    ExtractedData,
    GoogleSession,
    GoogleUser,
)

CLIENTS = "clients"
DOCUMENTS = "documents"
DOCUMENT_TYPES = "document_types"
DRIVE_WATCH_CHANNELS = "drive_watch_channels"
DRIVE_FILE_CLAIMS = "drive_file_claims"
DRIVE_FILE_CLAIM_FAILURES = "drive_file_claim_failures"
EXTRACTED_DATA = "extracted_data"
SESSIONS = "sessions"


def _as_utc(value: datetime) -> datetime:
    """Firestore hands back its own tz-aware datetime subclass; normalize it."""
    return value.astimezone(UTC)


def _increment_attempts(transaction, ref) -> int:
    """Reads-then-writes the attempt counter inside a transaction, so two
    concurrent handlers recording a failure for the same key cannot both read
    the same starting count and silently drop one increment."""
    with transaction:
        snapshot = ref.get(transaction=transaction)
        attempts = (snapshot.to_dict() or {}).get("attempts", 0) + 1 if snapshot.exists else 1
        transaction.set(ref, {"attempts": attempts})
    return attempts


class FirestoreClientRepository:
    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(CLIENTS)

    def save(self, client: Client) -> None:
        self._collection.document(client.id).set(
            {
                "name": client.name,
                "tax_id": client.tax_id,
                "email": client.email,
                "created_at": client.created_at,
                "drive_folder_id": client.drive_folder_id,
            }
        )

    def get(self, client_id: str) -> Client | None:
        snapshot = self._collection.document(client_id).get()
        return self._to_entity(snapshot.id, snapshot.to_dict()) if snapshot.exists else None

    def list_all(self) -> list[Client]:
        return [self._to_entity(d.id, d.to_dict()) for d in self._collection.stream()]

    @staticmethod
    def _to_entity(doc_id: str, data: dict[str, Any]) -> Client:
        return Client(
            id=doc_id,
            name=data["name"],
            tax_id=data.get("tax_id"),
            email=data.get("email"),
            created_at=_as_utc(data["created_at"]),
            drive_folder_id=data.get("drive_folder_id"),
        )


class FirestoreDocumentRepository:
    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(DOCUMENTS)

    def save(self, document: Document) -> None:
        self._collection.document(document.id).set(
            {
                "client_id": document.client_id,
                "document_type_id": document.document_type_id,
                "drive_file_id": document.drive_file_id,
                "file_name": document.file_name,
                "mime_type": document.mime_type,
                "status": str(document.status),
                "error": document.error,
                "created_at": document.created_at,
            }
        )

    def get(self, document_id: str) -> Document | None:
        snapshot = self._collection.document(document_id).get()
        return self._to_entity(snapshot.id, snapshot.to_dict()) if snapshot.exists else None

    def list_by_client(self, client_id: str) -> list[Document]:
        query = self._collection.where("client_id", "==", client_id)
        return [self._to_entity(d.id, d.to_dict()) for d in query.stream()]

    def get_by_drive_file_id_and_client(
        self, drive_file_id: str, client_id: str
    ) -> Document | None:
        query = (
            self._collection.where("drive_file_id", "==", drive_file_id)
            .where("client_id", "==", client_id)
            .limit(1)
        )
        for snapshot in query.stream():
            return self._to_entity(snapshot.id, snapshot.to_dict())
        return None

    @staticmethod
    def _to_entity(doc_id: str, data: dict[str, Any]) -> Document:
        return Document(
            id=doc_id,
            client_id=data["client_id"],
            document_type_id=data.get("document_type_id"),
            drive_file_id=data["drive_file_id"],
            file_name=data["file_name"],
            mime_type=data["mime_type"],
            status=DocumentStatus(data["status"]),
            error=data.get("error"),
            created_at=_as_utc(data["created_at"]),
        )


class FirestoreDocumentTypeRepository:
    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(DOCUMENT_TYPES)

    def save(self, document_type: DocumentType) -> None:
        self._collection.document(document_type.id).set(
            {
                "name": document_type.name,
                "description": document_type.description,
                "extraction_prompt": document_type.extraction_prompt,
                "extraction_schema": document_type.extraction_schema,
                "active": document_type.active,
                "created_at": document_type.created_at,
            }
        )

    def get(self, document_type_id: str) -> DocumentType | None:
        snapshot = self._collection.document(document_type_id).get()
        return self._to_entity(snapshot.id, snapshot.to_dict()) if snapshot.exists else None

    def list_active(self) -> list[DocumentType]:
        query = self._collection.where("active", "==", True)
        return [self._to_entity(d.id, d.to_dict()) for d in query.stream()]

    @staticmethod
    def _to_entity(doc_id: str, data: dict[str, Any]) -> DocumentType:
        return DocumentType(
            id=doc_id,
            name=data["name"],
            description=data["description"],
            extraction_prompt=data["extraction_prompt"],
            extraction_schema=data["extraction_schema"],
            active=data["active"],
            created_at=_as_utc(data["created_at"]),
        )


class FirestoreExtractedDataRepository:
    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(EXTRACTED_DATA)

    def save(self, extracted_data: ExtractedData) -> None:
        self._collection.document(extracted_data.id).set(
            {
                "document_id": extracted_data.document_id,
                "fields": extracted_data.fields,
                "confidence": extracted_data.confidence,
                "created_at": extracted_data.created_at,
            }
        )

    def get_by_document(self, document_id: str) -> ExtractedData | None:
        query = self._collection.where("document_id", "==", document_id).limit(1)
        for snapshot in query.stream():
            return self._to_entity(snapshot.id, snapshot.to_dict())
        return None

    @staticmethod
    def _to_entity(doc_id: str, data: dict[str, Any]) -> ExtractedData:
        return ExtractedData(
            id=doc_id,
            document_id=data["document_id"],
            fields=data["fields"],
            confidence=data.get("confidence"),
            created_at=_as_utc(data["created_at"]),
        )


class FirestoreSessionRepository:
    """Stores login sessions, including the Google refresh token.

    This collection holds credentials that grant read access to a user's Drive:
    it must never be exposed through an API, and its security rules should deny
    all client access (the server reaches it with admin credentials).
    """

    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(SESSIONS)

    def save(self, session: GoogleSession) -> None:
        self._collection.document(session.id).set(
            {
                "email": session.user.email,
                "name": session.user.name,
                "picture": session.user.picture,
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at,
                # Also the field a Firestore TTL policy should be configured on,
                # so abandoned grants do not live forever.
                "created_at": session.created_at,
            }
        )

    def get(self, session_id: str) -> GoogleSession | None:
        snapshot = self._collection.document(session_id).get()
        if not snapshot.exists:
            return None

        data = snapshot.to_dict()
        return GoogleSession(
            id=snapshot.id,
            user=GoogleUser(email=data["email"], name=data["name"], picture=data.get("picture")),
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=_as_utc(data["expires_at"]),
            created_at=_as_utc(data["created_at"]),
        )

    def delete(self, session_id: str) -> None:
        self._collection.document(session_id).delete()

    def delete_for_user(self, email: str) -> None:
        for snapshot in self._collection.where("email", "==", email).stream():
            self._collection.document(snapshot.id).delete()


class FirestoreDriveWatchChannelRepository:
    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(DRIVE_WATCH_CHANNELS)

    def save(self, channel: DriveWatchChannel) -> None:
        self._collection.document(channel.id).set(
            {
                "client_id": channel.client_id,
                "folder_id": channel.folder_id,
                "resource_id": channel.resource_id,
                "token": channel.token,
                "page_token": channel.page_token,
                "expires_at": channel.expires_at,
            }
        )

    def get_by_channel_id(self, channel_id: str) -> DriveWatchChannel | None:
        snapshot = self._collection.document(channel_id).get()
        if not snapshot.exists:
            return None

        data = snapshot.to_dict()
        return DriveWatchChannel(
            id=snapshot.id,
            resource_id=data["resource_id"],
            folder_id=data["folder_id"],
            client_id=data["client_id"],
            token=data["token"],
            page_token=data["page_token"],
            expires_at=_as_utc(data["expires_at"]),
        )


class FirestoreDriveFileClaimRepository:
    """Backs ``DriveFileClaimRepository.try_claim`` with Firestore's atomic
    document creation: ``create()`` fails with ``AlreadyExists`` instead of
    overwriting, which is what makes the claim safe under concurrent retries.

    A successful claim is never deleted, which is exactly what keeps a
    processed file from being picked up again; a Firestore TTL policy on
    ``claimed_at`` should still be configured so long-abandoned claims for
    since-deleted channels do not accumulate forever.
    """

    def __init__(self, db: FirestoreClient) -> None:
        self._db = db
        self._collection = db.collection(DRIVE_FILE_CLAIMS)
        self._failures = db.collection(DRIVE_FILE_CLAIM_FAILURES)

    def try_claim(self, key: str) -> bool:
        try:
            self._collection.document(key).create({"claimed_at": datetime.now(UTC)})
        except AlreadyExists:
            return False
        return True

    def release(self, key: str) -> None:
        self._collection.document(key).delete()

    def record_failure(self, key: str) -> int:
        # A transaction (not a plain get-then-set) is what keeps this correct
        # under two concurrent handlers recording a failure for the same key.
        transaction = self._db.transaction()
        return _increment_attempts(transaction, self._failures.document(key))

    def clear_failures(self, key: str) -> None:
        self._failures.document(key).delete()
