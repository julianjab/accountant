import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from server.application.use_cases.process_uploaded_document import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
)
from server.domain.entities import Document, DocumentStatus, ExtractedData
from server.domain.ports import (
    DocumentRepository,
    DocumentSourceParsers,
    DocumentStorage,
    ExtractedDataRepository,
)


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

    Two paths, chosen by the file rather than by the person:

    * A format with a dedicated parser (a tax authority's generated
      spreadsheet) is read exactly, with no AI in the path. Nobody is asked to
      pick it: the parsers say whether they recognise the bytes, which is a
      better answer than a menu, and a wrong pick was a real way to get stuck.
    * Anything else goes through classification and OCR against the configured
      document types, exactly as an arriving upload would.
    """

    def __init__(
        self,
        documents: DocumentRepository,
        storage: DocumentStorage,
        parsers: DocumentSourceParsers,
        extracted_data: ExtractedDataRepository,
        process_document: ProcessUploadedDocument,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._parsers = parsers
        self._extracted_data = extracted_data
        self._process_document = process_document

    def execute(self, data: ApproveDocumentInput) -> ApprovedDocument:
        document = self._documents.get(data.document_id)
        if document is None:
            raise DocumentNotFound(f"Document {data.document_id} not found")

        parsed = self._parse(document)
        if parsed is not None:
            self._save_extraction(document.id, parsed.summary)
            return ApprovedDocument(
                document=self._approve(document, data.approved_by, source_id=parsed.source_id),
                periods=parsed.periods,
            )

        # No parser claims this file, so it is a document like any other:
        # classified against the configured types and OCR'd with the winner's
        # prompt. Re-run rather than trusted, because the reason it is on this
        # screen is that an earlier run produced nothing usable — and a type
        # may well have been configured since.
        extracted = self._process_document.execute(
            ProcessUploadedDocumentInput(
                client_id=document.client_id,
                drive_file_id=document.drive_file_id,
                file_reference=document.drive_file_id,
                # Without this a second approval would leave a second document
                # behind for the same file.
                replace_existing=True,
            )
        )
        if extracted.status != DocumentStatus.PROCESSED:
            raise DocumentNotExtractable(
                extracted.error or "Nothing could be extracted from this document"
            )
        return ApprovedDocument(document=self._approve(extracted, data.approved_by))

    def _parse(self, document: Document):
        """Whether a dedicated parser reads this file, and what it read.

        The media type is checked against the entity before the bytes are
        fetched, so the ordinary case — a PDF certificate, which no parser
        handles — never pays for a download it does not need.
        """
        if not self._parsers.handles(document.mime_type):
            return None
        return self._parsers.recognize(self._storage.download(document.drive_file_id))

    def _save_extraction(self, document_id: str, fields: dict) -> None:
        # One extraction per document, replacing whatever it held — the same
        # rule OCR follows. Reusing the row's id keeps that a replacement in
        # every repository, including ones keyed by id rather than document.
        existing = self._extracted_data.get_by_document(document_id)
        self._extracted_data.save(
            ExtractedData(
                id=existing.id if existing is not None else str(uuid.uuid4()),
                document_id=document_id,
                fields=fields,
                # A parser reads the file exactly or does not read it at all;
                # there is no per-field uncertainty to report, and inventing
                # 1.0 would put it on the same scale as an AI's guess.
                confidence=None,
                created_at=datetime.now(UTC),
            )
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
