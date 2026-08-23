from datetime import UTC, datetime, timedelta

from server.application.use_cases import GetDocumentMetrics
from server.domain.entities import Document, DocumentStatus
from server.infrastructure.adapters.in_memory_repositories import InMemoryDocumentRepository


def _document(**overrides) -> Document:
    defaults = dict(
        id="doc-1",
        client_id="client-1",
        document_type_id="type-1",
        drive_file_id="drive-1",
        file_name="doc.pdf",
        mime_type="application/pdf",
        status=DocumentStatus.PENDING,
        error=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Document(**defaults)


def test_get_document_metrics_counts_by_status_and_averages_processing_time() -> None:
    documents = InMemoryDocumentRepository()
    now = datetime.now(UTC)
    documents.save(_document(id="doc-1", status=DocumentStatus.PENDING))
    documents.save(_document(id="doc-2", status=DocumentStatus.FAILED))
    documents.save(
        _document(
            id="doc-3",
            status=DocumentStatus.PROCESSED,
            created_at=now - timedelta(seconds=10),
            processed_at=now,
        )
    )

    metrics = GetDocumentMetrics(documents).execute()

    assert metrics.unprocessed == 1
    assert metrics.failed == 1
    assert metrics.processed_today == 1
    assert metrics.avg_processing_seconds == 10.0


def test_get_document_metrics_avg_is_none_without_processed_documents() -> None:
    documents = InMemoryDocumentRepository()
    documents.save(_document(id="doc-1", status=DocumentStatus.PENDING))

    metrics = GetDocumentMetrics(documents).execute()

    assert metrics.avg_processing_seconds is None
    assert metrics.processed_today == 0
