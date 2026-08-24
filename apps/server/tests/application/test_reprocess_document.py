"""Re-reading one document on purpose, approved or not.

The folder import refuses to touch an APPROVED document so that syncing a
folder can never undo a review. This is the act that is allowed to: it names a
single document, and it hands back a reading nobody has signed off on yet.
"""

from __future__ import annotations

from datetime import UTC, datetime

import fixtures
import pytest

from server.application.use_cases import (
    DocumentNotFound,
    ExtractDocument,
    ProcessUploadedDocument,
    ReprocessDocument,
    ReprocessDocumentInput,
)
from server.domain.entities import Document, DocumentStatus, DocumentType, ExtractedData
from server.domain.ports import DocumentContent
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
    InMemoryExtractedDataRepository,
)
from server.reconciliation.core.registry import KindRegistry
from server.reconciliation.infrastructure import KindSourceParsers
from server.reconciliation.kinds.exogena import ExogenaReconciliation

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF = "application/pdf"


class _Storage:
    def __init__(self, data: bytes, mime_type: str, file_name: str = "f") -> None:
        self._content = DocumentContent(data=data, mime_type=mime_type, file_name=file_name)

    def download(self, file_reference: str) -> DocumentContent:
        return self._content

    def list_files(self, folder_reference: str):
        return []


class _Classifier:
    def __init__(self, picks: DocumentType | None) -> None:
        self._picks = picks

    def classify(self, content, available_types):
        return self._picks


class _Ocr:
    def __init__(self, fields: dict | None = None) -> None:
        self.fields = fields if fields is not None else {"amount": "100"}

    def extract(self, content, document_type):
        return self.fields


def _document(mime_type: str, status: DocumentStatus) -> Document:
    return Document(
        id="doc-1",
        client_id="client-1",
        document_type_id="type-1" if mime_type == PDF else None,
        drive_file_id="drive-1",
        file_name="file",
        mime_type=mime_type,
        status=status,
        error=None,
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
        reviewed_at=datetime.now(UTC) if status == DocumentStatus.APPROVED else None,
        approved_by="jane" if status == DocumentStatus.APPROVED else None,
    )


def _a_type() -> DocumentType:
    return DocumentType(
        id="type-1",
        name="Certificado Bancolombia",
        description="",
        extraction_prompt="read it",
        extraction_schema={"type": "object", "properties": {}},
        active=True,
        created_at=datetime.now(UTC),
    )


def _use_case(
    documents: InMemoryDocumentRepository,
    storage: _Storage,
    extracted: InMemoryExtractedDataRepository,
    *,
    classifier=None,
    types: list[DocumentType] | None = None,
    ocr=None,
) -> ReprocessDocument:
    document_types = InMemoryDocumentTypeRepository()
    for document_type in types or []:
        document_types.save(document_type)
    return ReprocessDocument(
        documents=documents,
        extract=ExtractDocument(
            storage=storage,
            parsers=KindSourceParsers(KindRegistry([ExogenaReconciliation()])),
            extracted_data=extracted,
            process_document=ProcessUploadedDocument(
                storage=storage,
                classifier=classifier or _Classifier(None),
                ocr=ocr or _Ocr(),
                documents=documents,
                document_types=document_types,
                extracted_data=extracted,
            ),
        ),
    )


def test_an_approved_document_is_read_again_and_loses_its_approval() -> None:
    """The whole reason this exists: the import would have skipped this
    document, and the extraction on it is the one the corrected type replaces.
    """
    documents = InMemoryDocumentRepository()
    documents.save(_document(PDF, DocumentStatus.APPROVED))
    extracted = InMemoryExtractedDataRepository()
    extracted.save(
        ExtractedData(
            id="ext-1",
            document_id="doc-1",
            fields={"amount": "stale"},
            confidence=None,
            created_at=datetime.now(UTC),
        )
    )

    reprocessed = _use_case(
        documents,
        _Storage(b"a pdf", PDF),
        extracted,
        classifier=_Classifier(_a_type()),
        types=[_a_type()],
        ocr=_Ocr({"amount": "200"}),
    ).execute(ReprocessDocumentInput(document_id="doc-1"))

    assert reprocessed.document.status == DocumentStatus.PROCESSED
    # A fresh reading nobody has looked at: recording it as still approved
    # would attribute to a person a result they never saw.
    assert reprocessed.document.approved_by is None
    assert reprocessed.document.reviewed_at is None
    stored = extracted.get_by_document("doc-1")
    assert stored is not None
    assert stored.fields == {"amount": "200"}


def test_reprocessing_leaves_one_document_not_two() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(PDF, DocumentStatus.APPROVED))

    _use_case(
        documents,
        _Storage(b"a pdf", PDF),
        InMemoryExtractedDataRepository(),
        classifier=_Classifier(_a_type()),
        types=[_a_type()],
    ).execute(ReprocessDocumentInput(document_id="doc-1"))

    assert [d.id for d in documents.list_by_client("client-1")] == ["doc-1"]


def test_a_reading_that_fails_is_returned_rather_than_raised() -> None:
    """The reread already replaced what the document held by the time the
    classifier came up empty, so the FAILED document *is* the outcome."""
    documents = InMemoryDocumentRepository()
    documents.save(_document(PDF, DocumentStatus.APPROVED))

    reprocessed = _use_case(
        documents, _Storage(b"a pdf", PDF), InMemoryExtractedDataRepository()
    ).execute(ReprocessDocumentInput(document_id="doc-1"))

    assert reprocessed.document.status == DocumentStatus.FAILED
    assert reprocessed.document.approved_by is None
    assert documents.get("doc-1").status == DocumentStatus.FAILED


def test_a_file_with_its_own_parser_is_read_by_it_and_not_by_an_ai() -> None:
    """Same choice approving makes, and for the same reason — the parsers say
    whether they recognise the bytes. An AI must never be handed the exogena."""
    documents = InMemoryDocumentRepository()
    documents.save(_document(XLSX, DocumentStatus.APPROVED))
    extracted = InMemoryExtractedDataRepository()

    reprocessed = _use_case(
        documents, _Storage(fixtures.exogena_workbook_bytes(), XLSX), extracted
    ).execute(ReprocessDocumentInput(document_id="doc-1"))

    assert reprocessed.document.status == DocumentStatus.PROCESSED
    assert reprocessed.document.source_id == "exogena_report"
    assert reprocessed.document.approved_by is None
    assert reprocessed.document.error is None
    # The file states the year it covers, so the caller knows which reports
    # just went stale.
    assert reprocessed.periods == ("2025",)
    stored = extracted.get_by_document("doc-1")
    assert stored is not None
    assert stored.fields["periods"] == ["2025"]


def test_a_spreadsheet_that_is_not_the_report_falls_back_to_the_types() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(XLSX, DocumentStatus.PROCESSED))

    reprocessed = _use_case(
        documents,
        _Storage(b"not a workbook", XLSX),
        InMemoryExtractedDataRepository(),
        classifier=_Classifier(_a_type()),
        types=[_a_type()],
    ).execute(ReprocessDocumentInput(document_id="doc-1"))

    assert reprocessed.document.source_id is None
    assert reprocessed.document.document_type_id == "type-1"


def test_reprocessing_a_missing_document_is_reported_as_such() -> None:
    with pytest.raises(DocumentNotFound):
        _use_case(
            InMemoryDocumentRepository(),
            _Storage(b"a pdf", PDF),
            InMemoryExtractedDataRepository(),
        ).execute(ReprocessDocumentInput(document_id="nope"))
