from dataclasses import dataclass

from server.application.use_cases.approve_document import DocumentNotFound
from server.domain.entities import Document, DocumentStatus
from server.domain.ports import DocumentRepository


class DocumentNotApproved(Exception):
    """Raised when reopening a document nobody had approved.

    Distinguished from a successful reopen rather than treated as a no-op: it
    tells the caller their view is stale, where a silent success would let a
    wrong id read as a job well done.
    """


@dataclass(frozen=True, slots=True)
class ReopenDocumentInput:
    document_id: str


class ReopenDocument:
    """Withdraws an approval, returning the document to review.

    The deliberate act the rest of the system already assumes exists. Approval
    is protected everywhere: a re-import will not reprocess an approved
    document ("undoing it has to be a deliberate act of its own, not a side
    effect of re-importing a folder"), and a document cannot be re-read as a
    different source while it stands. Both were written against an undo that
    had not been built, which left an approval — including one made by
    mistake, on the wrong format — permanent.

    Withdrawing it removes the document from the spreadsheet export, which is
    the point: the export is defined as the approved documents, and a document
    under review is not one of them.
    """

    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    def execute(self, data: ReopenDocumentInput) -> Document:
        document = self._documents.get(data.document_id)
        if document is None:
            raise DocumentNotFound(f"Document {data.document_id} not found")
        if document.status != DocumentStatus.APPROVED:
            raise DocumentNotApproved(
                f"Document {data.document_id} is not approved; its status is {document.status}"
            )

        reopened = Document(
            id=document.id,
            client_id=document.client_id,
            document_type_id=document.document_type_id,
            drive_file_id=document.drive_file_id,
            file_name=document.file_name,
            mime_type=document.mime_type,
            # Back to where approval found it. The extraction is untouched:
            # withdrawing a review says nothing about what was read, only that
            # nobody stands behind it any more.
            status=DocumentStatus.PROCESSED,
            error=None,
            created_at=document.created_at,
            processed_at=document.processed_at,
            # Cleared rather than kept: leaving them behind would show the
            # document as reviewed by someone who has just withdrawn that.
            reviewed_at=None,
            approved_by=None,
            source_id=document.source_id,
        )
        self._documents.save(reopened)
        return reopened
