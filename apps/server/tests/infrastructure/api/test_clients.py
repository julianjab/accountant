from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import Client, Document, DocumentStatus
from server.infrastructure.api.auth_dependency import require_session
from server.infrastructure.api.deps import get_client_repository, get_document_repository
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
def client() -> TestClient:
    app.dependency_overrides[require_session] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


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
