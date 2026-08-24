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


def test_approving_reads_the_document_and_signs_off_on_it(client, documents, drive) -> None:
    """One endpoint because it is one button: a document reaches this screen
    precisely when the pipeline could make nothing of it."""
    import fixtures

    drive["data"] = fixtures.exogena_workbook_bytes()
    documents.save(
        _document(
            id="doc-1",
            status=DocumentStatus.FAILED,
            document_type_id=None,
            error="Could not identify the document type",
            file_name="reporteExogena2025.xlsx",
            mime_type=XLSX,
        )
    )

    response = client.post("/documents/doc-1/approve", json={"approved_by": "jane"})

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["source_id"] == "exogena_report"


def test_approving_a_missing_document_is_a_404(client, documents, drive) -> None:
    assert client.post("/documents/missing/approve").status_code == 404


def test_a_document_nothing_can_be_read_from_is_a_422(client, documents, drive) -> None:
    """Well formed request, entitled caller — the file itself yielded nothing."""
    documents.save(
        _document(
            id="doc-1",
            status=DocumentStatus.FAILED,
            document_type_id=None,
            file_name="notes.xlsx",
            mime_type=XLSX,
        )
    )

    assert client.post("/documents/doc-1/approve").status_code == 422
