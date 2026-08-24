"""Approving the exogena populates the client's cross-check.

The whole point of the button: press it once and the client's screens have
something to say — the rows third parties reported, and which of them nothing
backs yet.
"""

from __future__ import annotations

from datetime import UTC, datetime

import fixtures

from server.application.use_cases import (
    ApproveDocument,
    ApproveDocumentInput,
    ExtractDocument,
    ProcessUploadedDocument,
    ReprocessDocument,
    ReprocessDocumentInput,
)
from server.domain.entities import Client, Document, DocumentStatus
from server.domain.ports import DocumentContent
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryClientRepository,
    InMemoryDocumentRepository,
    InMemoryDocumentTypeRepository,
    InMemoryExtractedDataRepository,
)
from server.reconciliation.application.reconcile_client_period import (
    ReconcileClientPeriod,
    ReconcileClientPeriodInput,
)
from server.reconciliation.core.registry import KindRegistry
from server.reconciliation.infrastructure import (
    ApproveDocumentAndReconcile,
    DocumentFactProvider,
    InMemoryConceptMappingRepository,
    InMemoryReconciliationReportRepository,
    KindSourceParsers,
    ReprocessDocumentAndReconcile,
)
from server.reconciliation.kinds.exogena import ExogenaReconciliation
from server.shared import Period

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
KIND_ID = "exogena_dian"


class _Storage:
    def __init__(self, data: bytes) -> None:
        self._content = DocumentContent(
            data=data, mime_type=XLSX, file_name="reporteExogena2025.xlsx"
        )

    def download(self, file_reference: str) -> DocumentContent:
        return self._content

    def list_files(self, folder_reference: str):
        return []


class _RecordingReconcile:
    def __init__(self, fails: bool = False) -> None:
        self.calls: list[ReconcileClientPeriodInput] = []
        self._fails = fails

    def execute(self, data: ReconcileClientPeriodInput):
        self.calls.append(data)
        if self._fails:
            raise RuntimeError("the engine is down")
        return None


class _NeverClassifies:
    def classify(self, content, available_types):
        return None


class _Ocr:
    def extract(self, content, document_type):
        return {}


def _failed_exogena(year: int = 2025) -> Document:
    return Document(
        id="doc-1",
        client_id="client-1",
        document_type_id=None,
        drive_file_id="drive-1",
        file_name=f"reporteExogena{year}.xlsx",
        mime_type=XLSX,
        status=DocumentStatus.FAILED,
        error="Could not identify the document type",
        created_at=datetime.now(UTC),
    )


def _build(reconcile, data: bytes, documents=None, extracted=None, clients=None, reports=None):
    documents = documents if documents is not None else InMemoryDocumentRepository()
    extracted = extracted if extracted is not None else InMemoryExtractedDataRepository()
    registry = KindRegistry([ExogenaReconciliation()])
    storage = _Storage(data)
    document_types = InMemoryDocumentTypeRepository()
    return ApproveDocumentAndReconcile(
        approve=ApproveDocument(
            documents=documents,
            extract=ExtractDocument(
                storage=storage,
                parsers=KindSourceParsers(registry),
                extracted_data=extracted,
                process_document=ProcessUploadedDocument(
                    storage=storage,
                    classifier=_NeverClassifies(),
                    ocr=_Ocr(),
                    documents=documents,
                    document_types=document_types,
                    extracted_data=extracted,
                ),
            ),
        ),
        reconcile=reconcile,
        registry=registry,
    )


def test_approving_the_exogena_reconciles_the_year_the_file_states() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_failed_exogena())
    reconcile = _RecordingReconcile()

    _build(reconcile, fixtures.exogena_workbook_bytes(), documents=documents).execute(
        ApproveDocumentInput(document_id="doc-1")
    )

    assert [(c.client_id, c.kind_id, c.period) for c in reconcile.calls] == [
        ("client-1", KIND_ID, Period.of_year(2025))
    ]


def test_the_period_comes_from_the_file_and_not_from_the_screen() -> None:
    """A client's folder holds several years. Reconciling whichever year the
    screen has hardcoded would rebuild a report the document says nothing
    about, and leave the one it does change stale."""
    documents = InMemoryDocumentRepository()
    documents.save(_failed_exogena(2023))
    reconcile = _RecordingReconcile()

    _build(reconcile, fixtures.exogena_workbook_bytes(year=2023), documents=documents).execute(
        ApproveDocumentInput(document_id="doc-1")
    )

    assert [c.period for c in reconcile.calls] == [Period.of_year(2023)]


def test_a_reconciliation_that_fails_does_not_undo_the_approval() -> None:
    """The document is already saved by then. Failing the request would report
    an error for work that was done, and leave the reviewer believing nothing
    happened — while the reconciliation stays re-runnable on its own."""
    documents = InMemoryDocumentRepository()
    documents.save(_failed_exogena())

    approved = _build(
        _RecordingReconcile(fails=True), fixtures.exogena_workbook_bytes(), documents=documents
    ).execute(ApproveDocumentInput(document_id="doc-1"))

    assert approved.document.status == DocumentStatus.APPROVED
    assert documents.get("doc-1").status == DocumentStatus.APPROVED


def test_one_press_leaves_the_client_with_a_cross_check_to_read() -> None:
    """End to end against the real engine, in the state the accountant is
    actually in — no document types configured at all. Every row third parties
    reported is there, and nothing backs any of them yet."""
    documents = InMemoryDocumentRepository()
    documents.save(_failed_exogena())
    extracted = InMemoryExtractedDataRepository()
    clients = InMemoryClientRepository()
    clients.save(
        Client(
            id="client-1",
            name="Julian Buitrago",
            tax_id=fixtures.TAXPAYER_TAX_ID,
            email=None,
            created_at=datetime.now(UTC),
        )
    )
    reports = InMemoryReconciliationReportRepository()
    mappings = InMemoryConceptMappingRepository()
    registry = KindRegistry([ExogenaReconciliation()])
    storage = _Storage(fixtures.exogena_workbook_bytes())

    use_case = _build(
        ReconcileClientPeriod(
            registry=registry,
            facts=DocumentFactProvider(
                registry=registry,
                clients=clients,
                documents=documents,
                document_types=InMemoryDocumentTypeRepository(),
                extracted_data=extracted,
                mappings=mappings,
                storage=storage,
            ),
            reports=reports,
            mappings=mappings,
        ),
        fixtures.exogena_workbook_bytes(),
        documents=documents,
        extracted=extracted,
    )

    use_case.execute(ApproveDocumentInput(document_id="doc-1", approved_by="jane"))

    report = reports.get_latest("client-1", KIND_ID, Period.of_year(2025))
    assert report is not None, "the cross-check has to exist without pressing anything else"
    assert report.summary.total_findings > 0
    assert all(finding.evidence_facts == () for finding in report.findings), (
        "no certificates are configured, so nothing can back these rows yet"
    )


def _build_reprocess(reconcile, data: bytes, documents=None, extracted=None):
    documents = documents if documents is not None else InMemoryDocumentRepository()
    extracted = extracted if extracted is not None else InMemoryExtractedDataRepository()
    registry = KindRegistry([ExogenaReconciliation()])
    storage = _Storage(data)
    return ReprocessDocumentAndReconcile(
        reprocess=ReprocessDocument(
            documents=documents,
            extract=ExtractDocument(
                storage=storage,
                parsers=KindSourceParsers(registry),
                extracted_data=extracted,
                process_document=ProcessUploadedDocument(
                    storage=storage,
                    classifier=_NeverClassifies(),
                    ocr=_Ocr(),
                    documents=documents,
                    document_types=InMemoryDocumentTypeRepository(),
                    extracted_data=extracted,
                ),
            ),
        ),
        reconcile=reconcile,
        registry=registry,
    )


def test_reprocessing_rebuilds_the_report_the_reread_changed() -> None:
    """Reprocessing replaces the figures a report was built from, so leaving
    that report standing would show the client a cross-check of numbers that
    no longer exist."""
    documents = InMemoryDocumentRepository()
    approved = _failed_exogena()
    documents.save(
        Document(
            id=approved.id,
            client_id=approved.client_id,
            document_type_id=None,
            drive_file_id=approved.drive_file_id,
            file_name=approved.file_name,
            mime_type=approved.mime_type,
            status=DocumentStatus.APPROVED,
            error=None,
            created_at=approved.created_at,
            approved_by="jane",
            source_id="exogena_report",
        )
    )
    reconcile = _RecordingReconcile()

    reprocessed = _build_reprocess(
        reconcile, fixtures.exogena_workbook_bytes(), documents=documents
    ).execute(ReprocessDocumentInput(document_id="doc-1"))

    assert reprocessed.document.status == DocumentStatus.PROCESSED
    assert [(c.client_id, c.kind_id, c.period) for c in reconcile.calls] == [
        ("client-1", KIND_ID, Period.of_year(2025))
    ]
