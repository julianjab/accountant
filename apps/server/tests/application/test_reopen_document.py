"""Withdrawing an approval, so a document can be reviewed again.

The undo the rest of the system already assumed existed: a re-import refuses
to reprocess an approved document, and one cannot be re-read as a different
source while the approval stands. Both were written against this.
"""

from datetime import UTC, datetime

import pytest

from server.application.use_cases import (
    ApproveDocument,
    ApproveDocumentInput,
    DocumentNotApproved,
    DocumentNotFound,
    ReopenDocument,
    ReopenDocumentInput,
)
from server.domain.entities import Document, DocumentStatus
from server.infrastructure.adapters.in_memory_repositories import InMemoryDocumentRepository

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _document(status: DocumentStatus, **overrides) -> Document:
    defaults = dict(
        id="doc-1",
        client_id="client-1",
        document_type_id=None,
        drive_file_id="drive-1",
        file_name="reporteExogena2025.xlsx",
        mime_type=XLSX,
        status=status,
        error=None,
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
        source_id="exogena_report",
    )
    defaults.update(overrides)
    return Document(**defaults)


def test_reopening_returns_the_document_to_review() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(DocumentStatus.PROCESSED))
    ApproveDocument(documents).execute(
        ApproveDocumentInput(document_id="doc-1", approved_by="jane")
    )

    reopened = ReopenDocument(documents).execute(ReopenDocumentInput(document_id="doc-1"))

    assert reopened.status == DocumentStatus.PROCESSED
    # Cleared: leaving them would show the document as reviewed by someone who
    # has just withdrawn that.
    assert reopened.approved_by is None
    assert reopened.reviewed_at is None
    assert documents.get("doc-1") == reopened


def test_reopening_says_nothing_about_what_was_read() -> None:
    """Withdrawing a review is about who stands behind the document, not about
    its contents — so the extraction and what it was read as both survive."""
    documents = InMemoryDocumentRepository()
    documents.save(_document(DocumentStatus.APPROVED, approved_by="jane"))

    reopened = ReopenDocument(documents).execute(ReopenDocumentInput(document_id="doc-1"))

    assert reopened.source_id == "exogena_report"
    assert reopened.processed_at is not None


def test_a_reopened_document_can_be_approved_again() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(DocumentStatus.APPROVED, approved_by="jane"))
    ReopenDocument(documents).execute(ReopenDocumentInput(document_id="doc-1"))

    approved = ApproveDocument(documents).execute(
        ApproveDocumentInput(document_id="doc-1", approved_by="sam")
    )

    assert approved.status == DocumentStatus.APPROVED
    assert approved.approved_by == "sam"


def test_reopening_something_nobody_approved_is_refused() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(DocumentStatus.PROCESSED))

    with pytest.raises(DocumentNotApproved):
        ReopenDocument(documents).execute(ReopenDocumentInput(document_id="doc-1"))


def test_reopening_a_missing_document_is_reported_as_such() -> None:
    with pytest.raises(DocumentNotFound):
        ReopenDocument(InMemoryDocumentRepository()).execute(
            ReopenDocumentInput(document_id="missing")
        )
