from dataclasses import dataclass
from datetime import UTC, datetime

from server.application.use_cases.extract_document import ExtractDocument
from server.domain.entities import Document, DocumentStatus
from server.domain.ports import DocumentRepository


class DocumentNotFound(Exception):
    """Raised when the document to approve does not exist."""


class DocumentNotExtractable(Exception):
    """Raised when nothing could be read from the document.

    The approval does not happen: signing off on a document the system could
    make nothing of would put an empty row in the spreadsheet and record a
    person as having reviewed it.
    """


@dataclass(frozen=True, slots=True)
class ApproveDocumentInput:
    document_id: str
    approved_by: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovedDocument:
    """The document as it now stands, and what the file turned out to cover.

    The periods travel with it because approving is exactly the moment
    anything downstream goes stale, and the document itself is the only
    authority on which periods those are. A caller holding only the document
    would have to guess, or read the file again to find out.
    """

    document: Document
    periods: tuple[str, ...] = ()


class ApproveDocument:
    """Reads the document and signs off on the result, in one act.

    Deliberately not a review that assumes the work already happened. A
    document only reaches the accountant's screen at all when the pipeline
    could make nothing of it — the classifier has no configured type that
    matches, or the file is a format no AI should be reading in the first
    place — so "approve" with nothing behind it would sign off on an empty
    result. This is the button that does the work and accepts it.

    Which of the two reading paths runs is `ExtractDocument`'s decision, made
    from the file itself.
    """

    def __init__(self, documents: DocumentRepository, extract: ExtractDocument) -> None:
        self._documents = documents
        self._extract = extract

    def execute(self, data: ApproveDocumentInput) -> ApprovedDocument:
        document = self._documents.get(data.document_id)
        if document is None:
            raise DocumentNotFound(f"Document {data.document_id} not found")

        extraction = self._extract.execute(document)
        if extraction.source_id is None and extraction.document.status != DocumentStatus.PROCESSED:
            raise DocumentNotExtractable(
                extraction.document.error or "Nothing could be extracted from this document"
            )
        return ApprovedDocument(
            document=self._approve(
                extraction.document, data.approved_by, source_id=extraction.source_id
            ),
            periods=extraction.periods,
        )

    def _approve(
        self, document: Document, approved_by: str | None, source_id: str | None = None
    ) -> Document:
        approved = Document(
            id=document.id,
            client_id=document.client_id,
            document_type_id=document.document_type_id,
            drive_file_id=document.drive_file_id,
            file_name=document.file_name,
            mime_type=document.mime_type,
            status=DocumentStatus.APPROVED,
            error=None,
            created_at=document.created_at,
            processed_at=datetime.now(UTC),
            reviewed_at=datetime.now(UTC),
            approved_by=approved_by,
            # A file read by a parser has no document type by design, so this
            # is the only thing that can say what it was read as.
            source_id=source_id if source_id is not None else document.source_id,
        )
        self._documents.save(approved)
        return approved
