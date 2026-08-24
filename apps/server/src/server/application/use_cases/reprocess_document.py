from dataclasses import dataclass
from datetime import UTC, datetime

from server.application.use_cases.approve_document import DocumentNotFound
from server.application.use_cases.extract_document import ExtractDocument
from server.domain.entities import Document, DocumentStatus
from server.domain.ports import DocumentRepository


@dataclass(frozen=True, slots=True)
class ReprocessDocumentInput:
    document_id: str


@dataclass(frozen=True, slots=True)
class ReprocessedDocument:
    """The document as it now stands, and the periods the file covers.

    Same shape as an approval's result, and for the same reason: rereading a
    file is what makes anything downstream stale, and the file is the only
    authority on which periods those are.
    """

    document: Document
    periods: tuple[str, ...] = ()


class ReprocessDocument:
    """Reads one document's file again, on purpose, whatever state it is in.

    The folder import deliberately refuses to do this to an APPROVED document:
    a re-import must never undo a person's review as a side effect of syncing
    a folder. This is the act that may — it names a single document, and it is
    what a preparer needs after configuring or correcting the type that
    document belongs to, which is the whole reason its extraction is wrong.

    The approval does not survive, and that is the point rather than a
    casualty: what comes back is a fresh reading nobody has looked at, so the
    document lands back in PROCESSED and has to be approved again. Recording
    it as still approved would attribute to a person a result they never saw.

    A reading that fails is returned, not raised: unlike an approval — which
    can decline to sign off and leave everything as it was — the reread has
    already replaced what the document held by the time anything goes wrong,
    so the FAILED document *is* the outcome, and it stays re-runnable.
    """

    def __init__(self, documents: DocumentRepository, extract: ExtractDocument) -> None:
        self._documents = documents
        self._extract = extract

    def execute(self, data: ReprocessDocumentInput) -> ReprocessedDocument:
        document = self._documents.get(data.document_id)
        if document is None:
            raise DocumentNotFound(f"Document {data.document_id} not found")

        extraction = self._extract.execute(document)
        if extraction.source_id is None:
            # The OCR path rewrote the row itself — into PROCESSED or FAILED,
            # and with the approval fields blank, since it builds the document
            # afresh. Nothing left to do.
            return ReprocessedDocument(document=extraction.document)
        return ReprocessedDocument(
            document=self._mark_processed(extraction.document, extraction.source_id),
            periods=extraction.periods,
        )

    def _mark_processed(self, document: Document, source_id: str) -> Document:
        """Where the OCR path rewrites the row, the parser path leaves it
        alone — so an approved spreadsheet would keep saying `approved` over
        figures nobody has reviewed. This is that same reset, written out."""
        reprocessed = Document(
            id=document.id,
            client_id=document.client_id,
            document_type_id=document.document_type_id,
            drive_file_id=document.drive_file_id,
            file_name=document.file_name,
            mime_type=document.mime_type,
            status=DocumentStatus.PROCESSED,
            error=None,
            created_at=document.created_at,
            processed_at=datetime.now(UTC),
            reviewed_at=None,
            approved_by=None,
            source_id=source_id,
        )
        self._documents.save(reprocessed)
        return reprocessed
