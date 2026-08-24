"""Approving is the button that does the work and accepts the result.

A document only reaches the review screen when the pipeline could make nothing
of it — no configured type matched, or the file is a format no AI should be
reading. So approving extracts first, by whichever of the two paths the file
itself calls for, and only then signs off.
"""

from __future__ import annotations

from datetime import UTC, datetime

import fixtures
import pytest

from server.application.use_cases import (
    ApproveDocument,
    ApproveDocumentInput,
    DocumentNotExtractable,
    DocumentNotFound,
    ProcessUploadedDocument,
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
EXOGENA_SOURCE = "exogena_report"


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


def _document(mime_type: str, status: DocumentStatus = DocumentStatus.FAILED) -> Document:
    return Document(
        id="doc-1",
        client_id="client-1",
        document_type_id=None,
        drive_file_id="drive-1",
        file_name="file",
        mime_type=mime_type,
        status=status,
        error="Could not identify the document type",
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
) -> ApproveDocument:
    document_types = InMemoryDocumentTypeRepository()
    for document_type in types or []:
        document_types.save(document_type)
    return ApproveDocument(
        documents=documents,
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


def test_approving_the_exogena_reads_it_with_its_parser() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(XLSX))
    extracted = InMemoryExtractedDataRepository()

    approved = _use_case(
        documents, _Storage(fixtures.exogena_workbook_bytes(), XLSX), extracted
    ).execute(ApproveDocumentInput(document_id="doc-1", approved_by="jane"))

    assert approved.document.status == DocumentStatus.APPROVED
    assert approved.document.source_id == EXOGENA_SOURCE
    assert approved.document.error is None
    assert approved.document.approved_by == "jane"
    # The file states the year it covers, and it travels out so the caller
    # knows which reports just went stale.
    assert approved.periods == ("2025",)

    stored = extracted.get_by_document("doc-1")
    assert stored is not None
    assert stored.fields["reported_rows"] == len(fixtures.EXOGENA_ROWS)
    assert stored.fields["periods"] == ["2025"]


def test_nobody_is_asked_which_format_it_is() -> None:
    """The parsers answer from the bytes. A menu was a real way to get stuck:
    picking the wrong entry left the document read as something it is not."""
    documents = InMemoryDocumentRepository()
    documents.save(_document(XLSX))

    approved = _use_case(
        documents,
        _Storage(fixtures.exogena_workbook_bytes(), XLSX),
        InMemoryExtractedDataRepository(),
    ).execute(ApproveDocumentInput(document_id="doc-1"))

    assert approved.document.source_id == EXOGENA_SOURCE


def test_an_ordinary_document_is_classified_and_ocred_against_the_types() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(PDF))
    extracted = InMemoryExtractedDataRepository()
    document_type = _a_type()

    approved = _use_case(
        documents,
        _Storage(b"%PDF-1.4", PDF),
        extracted,
        classifier=_Classifier(document_type),
        types=[document_type],
        ocr=_Ocr({"amount": "1200"}),
    ).execute(ApproveDocumentInput(document_id="doc-1"))

    assert approved.document.status == DocumentStatus.APPROVED
    assert approved.document.document_type_id == "type-1"
    assert approved.document.source_id is None
    assert extracted.get_by_document("doc-1").fields == {"amount": "1200"}


def test_approving_re_runs_the_extraction_rather_than_trusting_an_old_one() -> None:
    """The reason a document is on this screen is that an earlier run produced
    nothing usable — and a type may well have been configured since."""
    documents = InMemoryDocumentRepository()
    documents.save(_document(PDF))
    extracted = InMemoryExtractedDataRepository()
    extracted.save(
        ExtractedData(
            id="extraction-1",
            document_id="doc-1",
            fields={"stale": True},
            confidence=0.2,
            created_at=datetime.now(UTC),
        )
    )
    document_type = _a_type()

    _use_case(
        documents,
        _Storage(b"%PDF-1.4", PDF),
        extracted,
        classifier=_Classifier(document_type),
        types=[document_type],
        ocr=_Ocr({"amount": "1200"}),
    ).execute(ApproveDocumentInput(document_id="doc-1"))

    stored = extracted.get_by_document("doc-1")
    assert "stale" not in stored.fields


def test_a_second_approval_leaves_one_document_not_two() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(PDF))
    document_type = _a_type()
    use_case = _use_case(
        documents,
        _Storage(b"%PDF-1.4", PDF),
        InMemoryExtractedDataRepository(),
        classifier=_Classifier(document_type),
        types=[document_type],
    )

    use_case.execute(ApproveDocumentInput(document_id="doc-1"))
    use_case.execute(ApproveDocumentInput(document_id="doc-1"))

    assert len(documents.list_by_client("client-1")) == 1


def test_a_document_nothing_can_be_read_from_is_not_approved() -> None:
    """Signing off on it would put an empty row in the spreadsheet and record a
    person as having reviewed it."""
    documents = InMemoryDocumentRepository()
    documents.save(_document(PDF))

    with pytest.raises(DocumentNotExtractable):
        _use_case(documents, _Storage(b"%PDF-1.4", PDF), InMemoryExtractedDataRepository()).execute(
            ApproveDocumentInput(document_id="doc-1")
        )

    assert documents.get("doc-1").status != DocumentStatus.APPROVED


def test_a_spreadsheet_that_is_not_the_report_falls_back_to_the_types() -> None:
    """A client's folder holds all sorts of spreadsheets. One the parser does
    not recognise is an ordinary document, not a failure."""
    documents = InMemoryDocumentRepository()
    documents.save(_document(XLSX))
    document_type = _a_type()

    approved = _use_case(
        documents,
        _Storage(b"not a workbook", XLSX),
        InMemoryExtractedDataRepository(),
        classifier=_Classifier(document_type),
        types=[document_type],
    ).execute(ApproveDocumentInput(document_id="doc-1"))

    assert approved.document.document_type_id == "type-1"
    assert approved.document.source_id is None


def test_approving_a_missing_document_is_reported_as_such() -> None:
    with pytest.raises(DocumentNotFound):
        _use_case(
            InMemoryDocumentRepository(),
            _Storage(b"", PDF),
            InMemoryExtractedDataRepository(),
        ).execute(ApproveDocumentInput(document_id="missing"))
