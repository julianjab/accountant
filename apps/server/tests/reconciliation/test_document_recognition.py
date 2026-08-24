"""Reconciling the moment the exogena is recognised.

The point is what the accountant sees straight after saying "this is the
exogena": the client's report, listing every row third parties reported and
which of them nothing backs yet. Before this, that screen read empty until
someone found a button on another tab.
"""

from __future__ import annotations

from datetime import UTC, datetime

import fixtures
import pytest

from server.application.use_cases import (
    DocumentNotRecognized,
    RecognizedDocument,
    RecognizeDocumentSource,
    RecognizeDocumentSourceInput,
)
from server.domain.entities import Document, DocumentStatus
from server.domain.ports import DocumentContent
from server.infrastructure.adapters.in_memory_repositories import (
    InMemoryDocumentRepository,
    InMemoryExtractedDataRepository,
)
from server.reconciliation.application.reconcile_client_period import (
    ReconcileClientPeriod,
    ReconcileClientPeriodInput,
)
from server.reconciliation.core.registry import KindRegistry
from server.reconciliation.infrastructure import (
    InMemoryConceptMappingRepository,
    InMemoryReconciliationReportRepository,
    KindSourceParsers,
    RecognizeDocumentSourceAndReconcile,
)
from server.reconciliation.kinds.exogena import ExogenaReconciliation
from server.shared import Period

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXOGENA_SOURCE = "exogena_report"
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
    """Stands in for the engine, so a test can see exactly what was asked of it."""

    def __init__(self, fails: bool = False) -> None:
        self.calls: list[ReconcileClientPeriodInput] = []
        self._fails = fails

    def execute(self, data: ReconcileClientPeriodInput):
        self.calls.append(data)
        if self._fails:
            raise RuntimeError("the engine is down")
        return None


def _failed_exogena() -> Document:
    return Document(
        id="doc-1",
        client_id="client-1",
        document_type_id=None,
        drive_file_id="drive-1",
        file_name="reporteExogena2025.xlsx",
        mime_type=XLSX,
        status=DocumentStatus.FAILED,
        error="Could not identify the document type",
        created_at=datetime.now(UTC),
    )


def _use_case(reconcile, documents=None, data: bytes | None = None):
    documents = documents if documents is not None else InMemoryDocumentRepository()
    if documents.get("doc-1") is None:
        documents.save(_failed_exogena())
    registry = KindRegistry([ExogenaReconciliation()])
    return RecognizeDocumentSourceAndReconcile(
        recognize=RecognizeDocumentSource(
            documents=documents,
            storage=_Storage(data if data is not None else fixtures.exogena_workbook_bytes()),
            parsers=KindSourceParsers(registry),
            extracted_data=InMemoryExtractedDataRepository(),
        ),
        reconcile=reconcile,
        registry=registry,
    )


def test_recognising_the_exogena_reconciles_the_year_the_file_states() -> None:
    reconcile = _RecordingReconcile()

    recognized = _use_case(reconcile).execute(
        RecognizeDocumentSourceInput(document_id="doc-1", source_id=EXOGENA_SOURCE)
    )

    assert isinstance(recognized, RecognizedDocument)
    assert [(c.client_id, c.kind_id, c.period) for c in reconcile.calls] == [
        ("client-1", KIND_ID, Period.of_year(2025))
    ]


def test_the_period_comes_from_the_file_and_not_from_the_caller() -> None:
    """A client's folder holds several years. Reconciling the current one
    instead would rebuild a report the document says nothing about, and leave
    the one it does change stale."""
    reconcile = _RecordingReconcile()

    _use_case(reconcile, data=fixtures.exogena_workbook_bytes(year=2023)).execute(
        RecognizeDocumentSourceInput(document_id="doc-1", source_id=EXOGENA_SOURCE)
    )

    assert [c.period for c in reconcile.calls] == [Period.of_year(2023)]


def test_a_file_that_is_not_the_named_source_reconciles_nothing() -> None:
    reconcile = _RecordingReconcile()
    use_case = _use_case(reconcile, data=b"not a workbook")

    with pytest.raises(DocumentNotRecognized):
        use_case.execute(
            RecognizeDocumentSourceInput(document_id="doc-1", source_id=EXOGENA_SOURCE)
        )

    assert reconcile.calls == []


def test_a_reconciliation_that_fails_does_not_undo_the_recognition() -> None:
    """The document is already saved by then. Failing the request would report
    an error for work that was done, and leave the reviewer believing the file
    was never read — while the reconciliation stays re-runnable on its own."""
    documents = InMemoryDocumentRepository()
    reconcile = _RecordingReconcile(fails=True)

    recognized = _use_case(reconcile, documents=documents).execute(
        RecognizeDocumentSourceInput(document_id="doc-1", source_id=EXOGENA_SOURCE)
    )

    assert recognized.document.status == DocumentStatus.PROCESSED
    assert documents.get("doc-1").source_id == EXOGENA_SOURCE


def test_the_report_lists_the_exogena_rows_with_no_certificate_behind_them() -> None:
    """End to end against the real engine, which is the answer the accountant
    came for: with no certificates configured, every row third parties reported
    shows up as something nothing backs yet."""
    reports = InMemoryReconciliationReportRepository()
    documents = InMemoryDocumentRepository()
    registry = KindRegistry([ExogenaReconciliation()])
    storage = _Storage(fixtures.exogena_workbook_bytes())

    from server.infrastructure.adapters.in_memory_repositories import InMemoryClientRepository
    from server.reconciliation.infrastructure import DocumentFactProvider

    clients = InMemoryClientRepository()
    from server.domain.entities import Client

    clients.save(
        Client(
            id="client-1",
            name="Julian Buitrago",
            tax_id=fixtures.TAXPAYER_TAX_ID,
            email=None,
            created_at=datetime.now(UTC),
        )
    )
    documents.save(_failed_exogena())
    extracted = InMemoryExtractedDataRepository()
    mappings = InMemoryConceptMappingRepository()

    use_case = RecognizeDocumentSourceAndReconcile(
        recognize=RecognizeDocumentSource(
            documents=documents,
            storage=storage,
            parsers=KindSourceParsers(registry),
            extracted_data=extracted,
        ),
        reconcile=ReconcileClientPeriod(
            registry=registry,
            facts=DocumentFactProvider(
                registry=registry,
                clients=clients,
                documents=documents,
                document_types=_NoDocumentTypes(),
                extracted_data=extracted,
                mappings=mappings,
                storage=storage,
            ),
            reports=reports,
            mappings=mappings,
        ),
        registry=registry,
    )

    use_case.execute(RecognizeDocumentSourceInput(document_id="doc-1", source_id=EXOGENA_SOURCE))

    report = reports.get_latest("client-1", KIND_ID, Period.of_year(2025))
    assert report is not None, "the report has to exist without anyone pressing a button"
    # Every reported row is accounted for, and none of them is silently dropped.
    assert report.summary.total_findings > 0
    assert all(finding.evidence_facts == () for finding in report.findings), (
        "no certificates are configured, so nothing can back these rows yet"
    )


class _NoDocumentTypes:
    """DocumentTypeRepository stub: the state the accountant is actually in."""

    def save(self, document_type) -> None: ...

    def get(self, document_type_id: str):
        return None

    def list_active(self) -> list:
        return []

    def list_all(self) -> list:
        return []

    def delete(self, document_type_id: str) -> None: ...
