import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

# The same error as approving a document that is not there, raised from the
# same place rather than shadowed by a second class of the same name.
from server.application.use_cases.approve_document import DocumentNotFound
from server.domain.entities import Document, DocumentStatus, ExtractedData
from server.domain.ports import (
    DocumentRepository,
    DocumentSourceParsers,
    DocumentStorage,
    ExtractedDataRepository,
    SourceNotParsable,
)


class DocumentAlreadyApproved(Exception):
    """Raised when re-reading a document a person already reviewed.

    Approval is a human act recorded against what was on screen at the time.
    Silently replacing that document's extraction would leave the approval
    standing over content nobody approved.
    """


class DocumentNotRecognized(Exception):
    """Raised when the file is not the source it was said to be."""


@dataclass(frozen=True, slots=True)
class RecognizeDocumentSourceInput:
    document_id: str
    source_id: str


class RecognizeDocumentSource:
    """Reads a document with a dedicated parser, at a person's say-so.

    The classifier can only choose among configured document types, and some
    documents deliberately have none — a tax authority's generated spreadsheet
    is read by an exact parser instead, because running a language model over a
    thousand-row financial table costs money per run, varies between runs, and
    can misread a digit the whole report then rests on. Such a file therefore
    always fails classification. This is how a person says what it is and gets
    it to a state that can be reviewed and approved.
    """

    def __init__(
        self,
        documents: DocumentRepository,
        storage: DocumentStorage,
        parsers: DocumentSourceParsers,
        extracted_data: ExtractedDataRepository,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._parsers = parsers
        self._extracted_data = extracted_data

    def execute(self, data: RecognizeDocumentSourceInput) -> Document:
        document = self._documents.get(data.document_id)
        if document is None:
            raise DocumentNotFound(f"Document {data.document_id} not found")
        if document.status == DocumentStatus.APPROVED:
            raise DocumentAlreadyApproved(
                f"Document {data.document_id} was already approved by "
                f"{document.approved_by or 'someone'}"
            )

        content = self._storage.download(document.drive_file_id)
        try:
            parsed = self._parsers.parse(content, data.source_id)
        except SourceNotParsable as exc:
            # Nothing is written: the document keeps whatever it had, so
            # choosing the wrong source and choosing the right one afterwards
            # leaves no trace of the first attempt.
            raise DocumentNotRecognized(str(exc)) from exc

        # One extraction per document, replacing whatever it held — the same
        # rule OCR follows. Reusing the row's id keeps that a replacement in
        # every repository, including ones keyed by id rather than document.
        existing = self._extracted_data.get_by_document(document.id)
        self._extracted_data.save(
            ExtractedData(
                id=existing.id if existing is not None else str(uuid.uuid4()),
                document_id=document.id,
                fields=parsed.summary,
                # A parser reads the file exactly or fails; there is no
                # per-field uncertainty to report, and inventing 1.0 would put
                # it on the same scale as an AI's guess.
                confidence=None,
                created_at=datetime.now(UTC),
            )
        )

        recognized = Document(
            id=document.id,
            client_id=document.client_id,
            # Still no document type, on purpose: this file is not extracted
            # against one, and pointing it at a type would make it look
            # configurable through the Config screens, which it is not.
            document_type_id=None,
            drive_file_id=document.drive_file_id,
            file_name=document.file_name,
            mime_type=document.mime_type,
            status=DocumentStatus.PROCESSED,
            error=None,
            created_at=document.created_at,
            processed_at=datetime.now(UTC),
            reviewed_at=document.reviewed_at,
            approved_by=document.approved_by,
            source_id=parsed.source_id,
        )
        self._documents.save(recognized)
        return recognized
