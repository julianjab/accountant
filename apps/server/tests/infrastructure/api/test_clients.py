from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from server.domain.entities import Client, Document, DocumentStatus, ExtractedData
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
