from datetime import UTC, datetime

import pytest

from server.application.use_cases import (
    ClientNotFound,
    ListClientSheetRows,
    ListClientSheetRowsInput,
)
from server.domain.entities import Client, Document, DocumentStatus, ExtractedData
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryClientRepository,
    InMemoryDocumentRepository,
    InMemoryExtractedDataRepository,
)


def _client() -> Client:
    return Client(
        id="client-1", name="Jane Doe", tax_id="123", email=None, created_at=datetime.now(UTC)
    )


def _document(document_id: str, status: DocumentStatus, client_id: str = "client-1") -> Document:
    return Document(
        id=document_id,
        client_id=client_id,
        document_type_id="type-1",
        drive_file_id=f"drive-{document_id}",
        file_name=f"{document_id}.pdf",
        mime_type="application/pdf",
        status=status,
        error=None,
        created_at=datetime.now(UTC),
    )


def test_list_client_sheet_rows_returns_only_approved_documents() -> None:
    clients = InMemoryClientRepository()
    clients.save(_client())
    documents = InMemoryDocumentRepository()
    documents.save(_document("doc-approved", DocumentStatus.APPROVED))
    documents.save(_document("doc-processed", DocumentStatus.PROCESSED))
    documents.save(_document("doc-other-client", DocumentStatus.APPROVED, client_id="client-2"))
    extracted_data = InMemoryExtractedDataRepository()
    extracted_data.save(
        ExtractedData(
            id="ed-1",
            document_id="doc-approved",
            fields={"date": "2026-01-05", "description": "Pago", "amount": "1000", "tax": "190"},
            confidence=0.95,
            created_at=datetime.now(UTC),
        )
    )
    use_case = ListClientSheetRows(clients, documents, extracted_data)

    rows = use_case.execute(ListClientSheetRowsInput(client_id="client-1"))

    assert len(rows) == 1
    row = rows[0]
    assert row.source_document_id == "doc-approved"
    assert row.source_document_file_name == "doc-approved.pdf"
    assert row.date == "2026-01-05"
    assert row.description == "Pago"
    assert row.amount == "1000"
    assert row.tax == "190"


def test_list_client_sheet_rows_defaults_missing_fields_to_empty_string() -> None:
    clients = InMemoryClientRepository()
    clients.save(_client())
    documents = InMemoryDocumentRepository()
    documents.save(_document("doc-approved", DocumentStatus.APPROVED))
    use_case = ListClientSheetRows(clients, documents, InMemoryExtractedDataRepository())

    rows = use_case.execute(ListClientSheetRowsInput(client_id="client-1"))

    assert rows == [
        rows[0].__class__(
            source_document_id="doc-approved",
            source_document_file_name="doc-approved.pdf",
            date="",
            description="",
            amount="",
            tax="",
        )
    ]


def test_list_client_sheet_rows_raises_when_client_missing() -> None:
    use_case = ListClientSheetRows(
        InMemoryClientRepository(), InMemoryDocumentRepository(), InMemoryExtractedDataRepository()
    )

    with pytest.raises(ClientNotFound):
        use_case.execute(ListClientSheetRowsInput(client_id="missing"))
