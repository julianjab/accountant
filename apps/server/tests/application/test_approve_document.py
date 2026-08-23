from datetime import UTC, datetime

import pytest

from server.application.use_cases import (
    ApproveDocument,
    ApproveDocumentInput,
    DocumentNotApprovable,
    DocumentNotFound,
)
from server.domain.entities import Document, DocumentStatus
from server.infrastructure.adapters.in_memory_repositories import InMemoryDocumentRepository


def _document(status: DocumentStatus) -> Document:
    return Document(
        id="doc-1",
        client_id="client-1",
        document_type_id="type-1",
        drive_file_id="drive-1",
        file_name="doc.pdf",
        mime_type="application/pdf",
        status=status,
        error=None,
        created_at=datetime.now(UTC),
    )


def test_approve_document_marks_processed_document_as_approved() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(DocumentStatus.PROCESSED))
    use_case = ApproveDocument(documents)

    approved = use_case.execute(ApproveDocumentInput(document_id="doc-1", approved_by="jane"))

    assert approved.status == DocumentStatus.APPROVED
    assert approved.approved_by == "jane"
    assert approved.reviewed_at is not None
    assert documents.get("doc-1") == approved


def test_approve_document_raises_when_document_missing() -> None:
    use_case = ApproveDocument(InMemoryDocumentRepository())

    with pytest.raises(DocumentNotFound):
        use_case.execute(ApproveDocumentInput(document_id="missing"))


def test_approve_document_raises_when_not_processed() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(DocumentStatus.PENDING))
    use_case = ApproveDocument(documents)

    with pytest.raises(DocumentNotApprovable):
        use_case.execute(ApproveDocumentInput(document_id="doc-1"))
