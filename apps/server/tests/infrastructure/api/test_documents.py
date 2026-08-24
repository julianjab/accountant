from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import Document, DocumentStatus
from server.infrastructure.adapters.in_memory_repositories import InMemoryDocumentRepository
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import get_document_repository
from server.main import app

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _document(**overrides) -> Document:
    defaults = dict(
        id="doc-1",
        client_id="client-1",
        document_type_id="type-1",
        drive_file_id="drive-1",
        file_name="doc.pdf",
        mime_type="application/pdf",
        status=DocumentStatus.PENDING,
        error=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Document(**defaults)


@pytest.fixture
def documents() -> InMemoryDocumentRepository:
    # get_approve_document_use_case() calls get_document_repository() directly
    # (not via Depends), so overriding the FastAPI dependency wouldn't reach
    # it — clear the lru_cache singleton instead so every consumer, DI or
    # not, sees the same fresh repository.
    get_document_repository.cache_clear()
    yield get_document_repository()
    get_document_repository.cache_clear()


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[require_session] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_documents_filters_by_status_and_client(client, documents) -> None:
    documents.save(_document(id="doc-1", client_id="client-1", status=DocumentStatus.PENDING))
    documents.save(_document(id="doc-2", client_id="client-1", status=DocumentStatus.PROCESSED))
    documents.save(_document(id="doc-3", client_id="client-2", status=DocumentStatus.PENDING))

    response = client.get("/documents", params={"status": "pending", "client_id": "client-1"})

    assert response.status_code == 200
    ids = [d["id"] for d in response.json()]
    assert ids == ["doc-1"]


def test_list_documents_rejects_invalid_status(client, documents) -> None:
    response = client.get("/documents", params={"status": "not-a-status"})

    assert response.status_code == 422


def test_document_metrics(client, documents) -> None:
    now = datetime.now(UTC)
    documents.save(_document(id="doc-1", status=DocumentStatus.PENDING, created_at=now))
    documents.save(_document(id="doc-2", status=DocumentStatus.FAILED, created_at=now))
    documents.save(
        _document(id="doc-3", status=DocumentStatus.PROCESSED, created_at=now, processed_at=now)
    )

    response = client.get("/documents/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["unprocessed"] == 1
    assert body["failed"] == 1
    assert body["processed_today"] == 1
    assert body["avg_processing_seconds"] == 0.0


def test_document_metrics_avg_is_null_without_processed_documents(client, documents) -> None:
    documents.save(_document(id="doc-1", status=DocumentStatus.PENDING))

    response = client.get("/documents/metrics")

    assert response.json()["avg_processing_seconds"] is None


def test_approve_document_happy_path(client, documents) -> None:
    documents.save(_document(id="doc-1", status=DocumentStatus.PROCESSED))

    response = client.post("/documents/doc-1/approve", json={"approved_by": "jane"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "jane"
    assert body["reviewed_at"] is not None


def test_approve_document_returns_404_when_missing(client, documents) -> None:
    response = client.post("/documents/missing/approve")

    assert response.status_code == 404


def test_approve_document_returns_409_when_not_processed(client, documents) -> None:
    documents.save(_document(id="doc-1", status=DocumentStatus.PENDING))

    response = client.post("/documents/doc-1/approve")

    assert response.status_code == 409


def test_the_parsable_sources_are_offered_for_a_person_to_pick(client) -> None:
    """The classifier can never propose these — they are read by a parser
    rather than configured as a document type — so the screen has to offer
    them itself."""
    response = client.get("/documents/sources")

    assert response.status_code == 200
    sources = response.json()
    exogena = next(s for s in sources if s["id"] == "exogena_report")
    assert "exógena" in exogena["label"].lower()
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in exogena["media_types"]
    )


def test_sources_is_not_read_as_a_document_id(client, documents) -> None:
    """`/documents/sources` sits under the same prefix as `/documents/{id}`;
    declared the other way round it would 404 for every caller."""
    assert client.get("/documents/sources").status_code == 200


@pytest.fixture
def drive(monkeypatch):
    """Keeps `/recognize` off a real Drive client.

    `get_recognize_document_source_use_case` builds the storage adapter eagerly,
    and `GoogleDriveStorage.__init__` reads a service-account file — so without
    this even the 404 path fails before it ever looks for the document.
    """
    from server.domain.ports import DocumentContent
    from server.infrastructure.api import deps

    holder = {"data": b"not a workbook"}

    class _Storage:
        def download(self, file_reference):
            return DocumentContent(data=holder["data"], mime_type=XLSX, file_name="notes.xlsx")

    monkeypatch.setattr(deps, "get_document_storage", lambda: _Storage())
    return holder


def test_recognizing_a_missing_document_is_a_404(client, documents, drive) -> None:
    response = client.post("/documents/missing/recognize", json={"source_id": "exogena_report"})

    assert response.status_code == 404


def test_a_file_that_is_not_the_named_source_is_a_422(client, documents, drive) -> None:
    """Well-formed request, entitled caller — the file simply is not what they
    said it was, which is about the content and not the request."""
    documents.save(
        _document(
            id="doc-1",
            status=DocumentStatus.FAILED,
            document_type_id=None,
            file_name="notes.xlsx",
            mime_type=XLSX,
        )
    )

    response = client.post("/documents/doc-1/recognize", json={"source_id": "exogena_report"})

    assert response.status_code == 422
    # Untouched: choosing the wrong source must leave nothing behind.
    assert documents.get("doc-1").status == DocumentStatus.FAILED
