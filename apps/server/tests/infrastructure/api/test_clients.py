from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import (
    Client,
    Document,
    DocumentStatus,
    DocumentType,
    ExtractedData,
)
from server.domain.ports import DocumentContent
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import (
    get_client_repository,
    get_document_repository,
    get_extracted_data_repository,
)
from server.main import app


@pytest.fixture
def clients():
    get_client_repository.cache_clear()
    yield get_client_repository()
    get_client_repository.cache_clear()


@pytest.fixture
def documents():
    get_document_repository.cache_clear()
    yield get_document_repository()
    get_document_repository.cache_clear()


@pytest.fixture
def extracted_data():
    get_extracted_data_repository.cache_clear()
    yield get_extracted_data_repository()
    get_extracted_data_repository.cache_clear()


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[require_session] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_client_rejects_non_https_drive_folder_url(client) -> None:
    response = client.post(
        "/clients",
        json={
            "name": "Jane Doe",
            "tax_id": "123",
            "drive_folder_url": "javascript:alert(document.cookie)",
        },
    )

    assert response.status_code == 422


def test_get_client(client, clients) -> None:
    clients.save(
        Client(
            id="client-1",
            name="Jane Doe",
            tax_id="123",
            email=None,
            created_at=datetime.now(UTC),
            drive_folder_url="https://drive.google.com/drive/folders/abc",
        )
    )

    response = client.get("/clients/client-1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "client-1"
    assert body["drive_folder_url"] == "https://drive.google.com/drive/folders/abc"


def test_get_client_returns_404_for_unknown_client(client, clients) -> None:
    response = client.get("/clients/missing")

    assert response.status_code == 404


def test_list_client_documents(client, clients, documents) -> None:
    clients.save(
        Client(
            id="client-1", name="Jane Doe", tax_id="123", email=None, created_at=datetime.now(UTC)
        )
    )
    documents.save(
        Document(
            id="doc-1",
            client_id="client-1",
            document_type_id=None,
            drive_file_id="drive-1",
            file_name="doc.pdf",
            mime_type="application/pdf",
            status=DocumentStatus.PENDING,
            error=None,
            created_at=datetime.now(UTC),
        )
    )
    documents.save(
        Document(
            id="doc-2",
            client_id="client-2",
            document_type_id=None,
            drive_file_id="drive-2",
            file_name="doc2.pdf",
            mime_type="application/pdf",
            status=DocumentStatus.PENDING,
            error=None,
            created_at=datetime.now(UTC),
        )
    )

    response = client.get("/clients/client-1/documents")

    assert response.status_code == 200
    ids = [d["id"] for d in response.json()]
    assert ids == ["doc-1"]


def test_list_client_documents_returns_404_for_unknown_client(client, clients) -> None:
    response = client.get("/clients/missing/documents")

    assert response.status_code == 404


def test_list_client_spreadsheet_rows(client, clients, documents, extracted_data) -> None:
    clients.save(
        Client(
            id="client-1", name="Jane Doe", tax_id="123", email=None, created_at=datetime.now(UTC)
        )
    )
    documents.save(
        Document(
            id="doc-1",
            client_id="client-1",
            document_type_id="type-1",
            drive_file_id="drive-1",
            file_name="doc.pdf",
            mime_type="application/pdf",
            status=DocumentStatus.APPROVED,
            error=None,
            created_at=datetime.now(UTC),
        )
    )
    extracted_data.save(
        ExtractedData(
            id="ed-1",
            document_id="doc-1",
            fields={"date": "2026-01-05", "description": "Pago", "amount": "1000", "tax": "190"},
            confidence=0.95,
            created_at=datetime.now(UTC),
        )
    )

    response = client.get("/clients/client-1/spreadsheet-rows")

    assert response.status_code == 200
    assert response.json() == [
        {
            "source_document_id": "doc-1",
            "source_document_file_name": "doc.pdf",
            "date": "2026-01-05",
            "description": "Pago",
            "amount": "1000",
            "tax": "190",
        }
    ]


def test_list_client_spreadsheet_rows_returns_404_for_unknown_client(client, clients) -> None:
    response = client.get("/clients/missing/spreadsheet-rows")

    assert response.status_code == 404


def test_create_client_accepts_https_spreadsheet_url(client, clients) -> None:
    response = client.post(
        "/clients",
        json={
            "name": "Jane Doe",
            "tax_id": "123",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/abc",
        },
    )

    assert response.status_code == 201
    assert response.json()["spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/abc"


def test_create_client_rejects_non_https_spreadsheet_url(client, clients) -> None:
    response = client.post(
        "/clients",
        json={"name": "Jane Doe", "tax_id": "123", "spreadsheet_url": "javascript:alert(1)"},
    )

    assert response.status_code == 422


class _ImportStorage:
    def __init__(self, files, unreadable=None):
        self._files = files
        self._unreadable = unreadable or set()

    def list_files(self, folder_reference):
        return self._files

    def download(self, file_reference):
        if file_reference in self._unreadable:
            raise RuntimeError("unavailable")
        return DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="f.pdf")


@pytest.fixture
def import_client(clients, documents):
    from server.application.use_cases import ImportClientDocuments, ProcessUploadedDocument
    from server.domain.ports import StoredFile
    from server.infrastructure.adapters.in_memory_repositories import (
        InMemoryDocumentTypeRepository,
        InMemoryExtractedDataRepository,
    )
    from server.infrastructure.api import deps

    document_type = DocumentType(
        id="t1",
        name="Certificado",
        description="d",
        extraction_prompt="p",
        extraction_schema={"type": "object"},
        active=True,
        created_at=datetime.now(UTC),
    )
    types = InMemoryDocumentTypeRepository()
    types.save(document_type)

    class _Classifier:
        def classify(self, content, available_types):
            return document_type

    class _Ocr:
        def extract(self, content, document_type):
            return {"saldo": "1"}

    storage = _ImportStorage([StoredFile(id="f1", name="f1.pdf", mime_type="application/pdf")])
    use_case = ImportClientDocuments(
        clients=clients,
        documents=documents,
        storage=storage,
        process_document=ProcessUploadedDocument(
            storage=storage,
            classifier=_Classifier(),
            ocr=_Ocr(),
            documents=documents,
            document_types=types,
            extracted_data=InMemoryExtractedDataRepository(),
        ),
    )
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[deps.get_import_client_documents_use_case] = lambda: use_case
    yield TestClient(app)
    app.dependency_overrides.clear()


def _saved_client(clients, folder_id="folder-1"):
    clients.save(
        Client(
            id="c-import",
            name="Cliente",
            tax_id=None,
            email=None,
            created_at=datetime.now(UTC),
            drive_folder_id=folder_id,
        )
    )


def test_import_client_documents_processes_the_folder(import_client, clients) -> None:
    _saved_client(clients)
    response = import_client.post("/clients/c-import/documents/import")
    assert response.status_code == 200
    body = response.json()
    assert len(body["imported"]) == 1
    assert body["skipped"] == 0
    assert body["failed"] == []


def test_import_client_documents_skips_what_already_succeeded(import_client, clients) -> None:
    _saved_client(clients)
    import_client.post("/clients/c-import/documents/import")
    second = import_client.post("/clients/c-import/documents/import").json()
    assert second["skipped"] == 1
    assert second["imported"] == []


def test_import_client_documents_can_be_forced(import_client, clients) -> None:
    _saved_client(clients)
    import_client.post("/clients/c-import/documents/import")
    forced = import_client.post("/clients/c-import/documents/import?reprocess=true").json()
    assert len(forced["imported"]) == 1


def test_import_client_documents_returns_404_for_an_unknown_client(import_client) -> None:
    assert import_client.post("/clients/nope/documents/import").status_code == 404


def test_import_client_documents_returns_409_when_no_folder_is_linked(
    import_client, clients
) -> None:
    """Reporting an empty import would read as "the folder has no files"."""
    _saved_client(clients, folder_id=None)
    response = import_client.post("/clients/c-import/documents/import")
    assert response.status_code == 409
    assert "not linked" in response.json()["detail"]
