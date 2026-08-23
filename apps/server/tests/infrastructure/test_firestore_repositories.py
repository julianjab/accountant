from datetime import UTC, datetime, timedelta

from google.api_core.exceptions import AlreadyExists

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
from server.infrastructure.adapters.firestore_repositories import (
    FirestoreClientRepository,
    FirestoreDocumentRepository,
    FirestoreDocumentTypeRepository,
    FirestoreDriveFileClaimRepository,
    FirestoreDriveWatchChannelRepository,
    FirestoreExtractedDataRepository,
    FirestoreSessionRepository,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class FakeDocumentRef:
    def __init__(self, collection: "FakeCollection", doc_id: str) -> None:
        self._collection = collection
        self._id = doc_id

    def set(self, data: dict) -> None:
        self._collection.data[self._id] = data

    def create(self, data: dict) -> None:
        if self._id in self._collection.data:
            raise AlreadyExists("already exists")
        self._collection.data[self._id] = data

    def get(self) -> "FakeSnapshot":
        return FakeSnapshot(self._id, self._collection.data.get(self._id))

    def delete(self) -> None:
        self._collection.data.pop(self._id, None)


class FakeSnapshot:
    def __init__(self, doc_id: str, data: dict | None) -> None:
        self.id = doc_id
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict | None:
        return self._data


class FakeQuery:
    def __init__(self, items: list[FakeSnapshot]) -> None:
        self._items = items

    def limit(self, count: int) -> "FakeQuery":
        return FakeQuery(self._items[:count])

    def stream(self):
        return iter(self._items)


class FakeCollection:
    def __init__(self) -> None:
        self.data: dict[str, dict] = {}

    def document(self, doc_id: str) -> FakeDocumentRef:
        return FakeDocumentRef(self, doc_id)

    def stream(self):
        return iter([FakeSnapshot(k, v) for k, v in self.data.items()])

    def where(self, field: str, op: str, value) -> FakeQuery:
        assert op == "=="
        return FakeQuery(
            [FakeSnapshot(k, v) for k, v in self.data.items() if v.get(field) == value]
        )


class FakeFirestore:
    def __init__(self) -> None:
        self._collections: dict[str, FakeCollection] = {}

    def collection(self, name: str) -> FakeCollection:
        return self._collections.setdefault(name, FakeCollection())


def test_client_round_trips():
    repo = FirestoreClientRepository(FakeFirestore())
    client = Client(id="c1", name="Jane", tax_id="123", email=None, created_at=NOW)

    repo.save(client)

    assert repo.get("c1") == client
    assert repo.list_all() == [client]


def test_client_get_returns_none_when_absent():
    assert FirestoreClientRepository(FakeFirestore()).get("nope") is None


def test_document_round_trips_and_filters_by_client():
    repo = FirestoreDocumentRepository(FakeFirestore())
    mine = Document(
        id="d1",
        client_id="c1",
        document_type_id=None,
        drive_file_id="f1",
        file_name="a.pdf",
        mime_type="application/pdf",
        status=DocumentStatus.PENDING,
        error=None,
        created_at=NOW,
    )
    other = Document(
        id="d2",
        client_id="c2",
        document_type_id="t1",
        drive_file_id="f2",
        file_name="b.pdf",
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        error=None,
        created_at=NOW,
    )
    repo.save(mine)
    repo.save(other)

    assert repo.get("d1") == mine
    # The status must survive the round trip as the enum, not a bare string.
    assert repo.get("d2").status is DocumentStatus.PROCESSED
    assert repo.list_by_client("c1") == [mine]


def test_document_get_returns_none_when_absent():
    assert FirestoreDocumentRepository(FakeFirestore()).get("nope") is None


def test_document_type_round_trips_and_lists_only_active():
    repo = FirestoreDocumentTypeRepository(FakeFirestore())
    active = DocumentType(
        id="t1",
        name="Statement",
        description="d",
        extraction_prompt="p",
        extraction_schema={"type": "object"},
        active=True,
        created_at=NOW,
    )
    inactive = DocumentType(
        id="t2",
        name="Old",
        description="d",
        extraction_prompt="p",
        extraction_schema={},
        active=False,
        created_at=NOW,
    )
    repo.save(active)
    repo.save(inactive)

    assert repo.get("t1") == active
    assert repo.list_active() == [active]


def test_document_type_get_returns_none_when_absent():
    assert FirestoreDocumentTypeRepository(FakeFirestore()).get("nope") is None


def test_extracted_data_is_found_by_document():
    repo = FirestoreExtractedDataRepository(FakeFirestore())
    data = ExtractedData(
        id="e1", document_id="d1", fields={"total": 10}, confidence=0.9, created_at=NOW
    )
    repo.save(data)

    assert repo.get_by_document("d1") == data
    assert repo.get_by_document("d2") is None


def test_session_round_trips_including_the_refresh_token():
    repo = FirestoreSessionRepository(FakeFirestore())
    session = GoogleSession(
        id="s1",
        user=GoogleUser(email="a@b.com", name="A B", picture=None),
        access_token="at",
        refresh_token="rt",
        expires_at=NOW + timedelta(hours=1),
        created_at=NOW,
    )
    repo.save(session)

    assert repo.get("s1") == session


def test_signing_in_again_clears_the_user_previous_sessions():
    repo = FirestoreSessionRepository(FakeFirestore())
    user = GoogleUser(email="a@b.com", name="A B", picture=None)
    for session_id in ("s1", "s2"):
        repo.save(
            GoogleSession(
                id=session_id,
                user=user,
                access_token="at",
                refresh_token="rt",
                expires_at=NOW,
                created_at=NOW,
            )
        )
    repo.save(
        GoogleSession(
            id="other",
            user=GoogleUser(email="z@b.com", name="Z", picture=None),
            access_token="at",
            refresh_token="rt",
            expires_at=NOW,
            created_at=NOW,
        )
    )

    repo.delete_for_user("a@b.com")

    assert repo.get("s1") is None
    assert repo.get("s2") is None
    assert repo.get("other") is not None


def test_session_get_returns_none_when_absent_and_delete_is_idempotent():
    repo = FirestoreSessionRepository(FakeFirestore())

    repo.delete("nope")

    assert repo.get("nope") is None


def test_drive_watch_channel_round_trips():
    repo = FirestoreDriveWatchChannelRepository(FakeFirestore())
    channel = DriveWatchChannel(
        id="ch1",
        resource_id="r1",
        folder_id="f1",
        client_id="c1",
        token="secret",
        page_token="p1",
        expires_at=NOW,
    )

    repo.save(channel)

    assert repo.get_by_channel_id("ch1") == channel


def test_drive_watch_channel_get_returns_none_when_absent():
    assert FirestoreDriveWatchChannelRepository(FakeFirestore()).get_by_channel_id("nope") is None


def test_drive_file_claim_succeeds_only_once():
    repo = FirestoreDriveFileClaimRepository(FakeFirestore())

    assert repo.try_claim("file-1") is True
    assert repo.try_claim("file-1") is False
