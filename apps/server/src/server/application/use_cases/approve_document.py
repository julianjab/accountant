from dataclasses import dataclass
from datetime import UTC, datetime

from server.domain.entities import Document, DocumentStatus
from server.domain.ports import DocumentRepository


class DocumentNotFound(Exception):
    """Raised when the document to approve does not exist."""


class DocumentNotApprovable(Exception):
    """Raised when a document is approved from a status other than PROCESSED."""


@dataclass(frozen=True, slots=True)
class ApproveDocumentInput:
    document_id: str
    approved_by: str | None = None


class ApproveDocument:
    """Marks a processed document as reviewed and approved, a precondition for
    exporting its extracted data (see #11)."""

    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    def execute(self, data: ApproveDocumentInput) -> Document:
        document = self._documents.get(data.document_id)
        if document is None:
            raise DocumentNotFound(f"Document {data.document_id} not found")
        if document.status != DocumentStatus.PROCESSED:
            raise DocumentNotApprovable(
                f"Document {data.document_id} is not approvable from status {document.status}"
            )

        approved = Document(
            id=document.id,
            client_id=document.client_id,
            document_type_id=document.document_type_id,
            drive_file_id=document.drive_file_id,
            file_name=document.file_name,
            mime_type=document.mime_type,
            status=DocumentStatus.APPROVED,
            error=document.error,
            created_at=document.created_at,
            processed_at=document.processed_at,
            reviewed_at=datetime.now(UTC),
            approved_by=data.approved_by,
            # Carried over, or approving a document read by a parser would drop
            # the only record of what it was read as — leaving it approved and
            # indistinguishable from one nothing could be made of.
            source_id=document.source_id,
        )
        self._documents.save(approved)
        return approved
