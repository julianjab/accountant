"""Reading the bytes of a document the system already holds.

Configuring a document type needs a sample, and the sample worth having is a
paper already in a client's folder: the saved type can point back at it, so
the field list stays checkable against the page it was derived from. An
uploaded copy cannot be pointed at, because its bytes are gone as soon as the
request ends.
"""

from datetime import UTC, datetime

import pytest

from server.application.use_cases import (
    DocumentNotFound,
    ReadStoredDocument,
    ReadStoredDocumentInput,
)
from server.domain.entities import Document, DocumentStatus
from server.domain.ports import DocumentContent

CONTENT = DocumentContent(data=b"%PDF-", mime_type="application/pdf", file_name="cert.pdf")


def _document(document_id: str = "doc-1", drive_file_id: str = "drive-1") -> Document:
    return Document(
        id=document_id,
        client_id="client-1",
        document_type_id=None,
        drive_file_id=drive_file_id,
        file_name="cert.pdf",
        mime_type="application/pdf",
        status=DocumentStatus.PENDING,
        error=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


class _Documents:
    def __init__(self, *documents: Document) -> None:
        self._by_id = {document.id: document for document in documents}

    def get(self, document_id: str) -> Document | None:
        return self._by_id.get(document_id)


class _Storage:
    def __init__(self) -> None:
        self.downloaded: list[str] = []

    def download(self, file_reference: str) -> DocumentContent:
        self.downloaded.append(file_reference)
        return CONTENT


def test_it_reads_the_drive_file_the_document_stands_for():
    storage = _Storage()

    content = ReadStoredDocument(_Documents(_document()), storage).execute(
        ReadStoredDocumentInput(document_id="doc-1")
    )

    assert content == CONTENT
    # The document id is ours; the file id is Drive's. Passing the wrong one
    # reaches Drive as a 404 for a file that exists.
    assert storage.downloaded == ["drive-1"]


def test_an_unknown_document_is_reported_rather_than_reaching_storage():
    """Otherwise the failure surfaces as a Drive error about a file reference
    that was never a file reference."""
    storage = _Storage()

    with pytest.raises(DocumentNotFound):
        ReadStoredDocument(_Documents(), storage).execute(
            ReadStoredDocumentInput(document_id="missing")
        )

    assert storage.downloaded == []
