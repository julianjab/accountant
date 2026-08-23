from dataclasses import dataclass
from datetime import UTC, datetime

from server.domain.entities import DocumentStatus
from server.domain.ports import DocumentRepository

_UNPROCESSED_STATUSES = {
    DocumentStatus.PENDING,
    DocumentStatus.CLASSIFYING,
    DocumentStatus.RUNNING_OCR,
}


@dataclass(frozen=True, slots=True)
class DocumentMetrics:
    unprocessed: int
    processed_today: int
    failed: int
    avg_processing_seconds: float | None


class GetDocumentMetrics:
    """Figures for the dashboard's metric cards. "Today" is computed in UTC."""

    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    def execute(self) -> DocumentMetrics:
        items = self._documents.list_all()
        today = datetime.now(UTC).date()

        unprocessed = sum(1 for d in items if d.status in _UNPROCESSED_STATUSES)
        failed = sum(1 for d in items if d.status == DocumentStatus.FAILED)
        processed = [d for d in items if d.status == DocumentStatus.PROCESSED]
        processed_today = sum(
            1
            for d in processed
            if d.processed_at is not None and d.processed_at.astimezone(UTC).date() == today
        )

        durations = [
            (d.processed_at - d.created_at).total_seconds()
            for d in processed
            if d.processed_at is not None
        ]
        avg_processing_seconds = sum(durations) / len(durations) if durations else None

        return DocumentMetrics(
            unprocessed=unprocessed,
            processed_today=processed_today,
            failed=failed,
            avg_processing_seconds=avg_processing_seconds,
        )
