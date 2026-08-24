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
from google.cloud.firestore import transactional

from server.domain.entities import (
    Client,
    Document,
    DocumentStatus,
    DocumentType,
    DocumentTypeField,
    DriveWatchChannel,
    ExtractedData,
    FieldRole,
    GoogleSession,
    GoogleUser,
)
from server.domain.ports.repositories import CLAIM_STALE_AFTER

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


def _as_utc_or_none(value: datetime | None) -> datetime | None:
    return None if value is None else _as_utc(value)


@transactional
def _increment_attempts(transaction, ref) -> int:
    """Reads-then-writes the attempt counter inside a transaction, so two
    concurrent handlers recording a failure for the same key cannot both read
    the same starting count and silently drop one increment.

    Must go through the ``@transactional`` decorator rather than a bare
    ``with transaction:``: ``Transaction`` never begins itself (it inherits
    ``WriteBatch.__enter__``, which is a no-op), so a plain context manager
    would try to commit a transaction that was never started. The decorator
    is what calls ``_begin()``/retries/`_commit()` correctly.
    """
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
                "drive_folder_url": client.drive_folder_url,
                "spreadsheet_url": client.spreadsheet_url,
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
            drive_folder_url=data.get("drive_folder_url"),
            spreadsheet_url=data.get("spreadsheet_url"),
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
                # Dropped before this: a document read back after approval
                # returned approved_by=None, so the approval survived only as
                # a status. Reconciliation refuses to reprocess an APPROVED
                # document precisely to protect that review, which is worth
                # nothing if who approved it and when are not stored.
                "processed_at": document.processed_at,
                "reviewed_at": document.reviewed_at,
                "approved_by": document.approved_by,
            }
        )

    def get(self, document_id: str) -> Document | None:
        snapshot = self._collection.document(document_id).get()
        return self._to_entity(snapshot.id, snapshot.to_dict()) if snapshot.exists else None

    def list_by_client(self, client_id: str) -> list[Document]:
        query = self._collection.where("client_id", "==", client_id)
        return [self._to_entity(d.id, d.to_dict()) for d in query.stream()]

    def list_all(self, status: DocumentStatus | None = None) -> list[Document]:
        query = (
            self._collection
            if status is None
            else self._collection.where("status", "==", str(status))
        )
        return [self._to_entity(d.id, d.to_dict()) for d in query.stream()]

    def get_by_drive_file_id_and_client(
        self, drive_file_id: str, client_id: str
    ) -> Document | None:
        # ProcessUploadedDocument reuses one row per (drive_file_id, client_id)
        # across retries, so this is almost always a single match; sorting
        # client-side (instead of an order_by on a third field, which would
        # need a composite index not covered by Firestore's automatic
        # single-field indexes) still returns the most recent one on the rare
        # chance more than one exists (e.g. a race between two attempts).
        query = self._collection.where("drive_file_id", "==", drive_file_id).where(
            "client_id", "==", client_id
        )
        documents = [self._to_entity(d.id, d.to_dict()) for d in query.stream()]
        return max(documents, key=lambda d: d.created_at, default=None)

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
            processed_at=_as_utc_or_none(data.get("processed_at")),
            reviewed_at=_as_utc_or_none(data.get("reviewed_at")),
            approved_by=data.get("approved_by"),
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
                "tax_years": list(document_type.tax_years),
                "sample_document_id": document_type.sample_document_id,
                "fields": [
                    {
                        "path": f.path,
                        "label": f.label,
                        "role": str(f.role),
                        "section": f.section,
                    }
                    for f in document_type.fields
                ],
            }
        )

    def get(self, document_type_id: str) -> DocumentType | None:
        snapshot = self._collection.document(document_type_id).get()
        return self._to_entity(snapshot.id, snapshot.to_dict()) if snapshot.exists else None

    def list_active(self) -> list[DocumentType]:
        query = self._collection.where("active", "==", True)
        return [self._to_entity(d.id, d.to_dict()) for d in query.stream()]

    def list_all(self) -> list[DocumentType]:
        return [self._to_entity(d.id, d.to_dict()) for d in self._collection.stream()]

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
            tax_years=tuple(data.get("tax_years") or ()),
            sample_document_id=data.get("sample_document_id"),
            fields=_document_type_fields(data.get("fields")),
        )


def _document_type_fields(raw: Any) -> tuple[DocumentTypeField, ...]:
    """Field descriptions as stored, skipping anything unreadable.

    Types created before descriptions existed have no `fields` at all, and a
    row written by an older shape must not make the whole type unreadable —
    losing a label degrades a screen, raising here loses the type.
    """
    if not isinstance(raw, list):
        return ()
    fields = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        try:
            role = FieldRole(item.get("role", FieldRole.CONTEXT))
        except ValueError:
            role = FieldRole.CONTEXT
        fields.append(
            DocumentTypeField(
                path=item["path"],
                label=item.get("label") or item["path"],
                role=role,
                section=item.get("section") or "",
            )
        )
    return tuple(fields)


class FirestoreExtractedDataRepository:
    """Keyed by document id, because a document has exactly one extraction.

    Keying by the extraction's own id let a re-run add a second row for the
    same document, and the read then picked between them with a `limit(1)` and
    no ordering — so re-running OCR to correct a bad extraction could keep
    serving the bad one. The entity's id is kept as a field; the storage key is
    the thing that has to be one per document.
    """

    def __init__(self, db: FirestoreClient) -> None:
        self._collection = db.collection(EXTRACTED_DATA)

    def save(self, extracted_data: ExtractedData) -> None:
        self._collection.document(extracted_data.document_id).set(
            {
                "id": extracted_data.id,
                "document_id": extracted_data.document_id,
                "fields": extracted_data.fields,
                "confidence": extracted_data.confidence,
                "created_at": extracted_data.created_at,
            }
        )

    def get_by_document(self, document_id: str) -> ExtractedData | None:
        snapshot = self._collection.document(document_id).get()
        if snapshot.exists:
            return self._to_entity(snapshot.id, snapshot.to_dict())
        # Rows written before the key changed live under the extraction's own
        # id, so a point read misses them. Falling back to the query keeps
        # already-processed documents readable without a migration, and the
        # ambiguity that motivated the new key cannot arise here: this runs
        # only when no row exists under it. The next save writes the new key
        # and the fallback stops being used for that document.
        for legacy in self._collection.where("document_id", "==", document_id).stream():
            return self._to_entity(legacy.id, legacy.to_dict())
        return None

    @staticmethod
    def _to_entity(doc_id: str, data: dict[str, Any]) -> ExtractedData:
        return ExtractedData(
            id=data.get("id", doc_id),
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
    since-deleted channels do not accumulate forever. A claim older than
    ``CLAIM_STALE_AFTER`` is reclaimable, which recovers from a process that
    crashed between claiming a file and ever recording an outcome for it.
    """

    def __init__(self, db: FirestoreClient) -> None:
        self._db = db
        self._collection = db.collection(DRIVE_FILE_CLAIMS)
        self._failures = db.collection(DRIVE_FILE_CLAIM_FAILURES)

    def try_claim(self, key: str) -> bool:
        doc_ref = self._collection.document(key)
        try:
            doc_ref.create({"claimed_at": datetime.now(UTC)})
            return True
        except AlreadyExists:
            pass

        # The claim already exists: only a crashed handler (nothing ever
        # released or re-recorded an outcome for it) makes it re-claimable.
        # A small race where two stale-reclaimers both succeed is accepted
        # rather than eliminated with a transaction: it is already idempotent
        # downstream, since ProcessUploadedDocument reuses non-PROCESSED rows.
        existing = doc_ref.get()
        claimed_at = existing.to_dict().get("claimed_at") if existing.exists else None
        if claimed_at is not None and datetime.now(UTC) - _as_utc(claimed_at) < CLAIM_STALE_AFTER:
            return False
        doc_ref.set({"claimed_at": datetime.now(UTC)})
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
