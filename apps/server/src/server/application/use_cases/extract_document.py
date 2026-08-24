import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from server.application.use_cases.process_uploaded_document import (
    ProcessUploadedDocument,
    ProcessUploadedDocumentInput,
)
from server.domain.entities import Document, ExtractedData
from server.domain.ports import (
    DocumentSourceParsers,
    DocumentStorage,
    ExtractedDataRepository,
)


@dataclass(frozen=True, slots=True)
class DocumentExtraction:
    """What reading a document's file produced, whichever path read it.

    `document` is the row as it now stands: rewritten by the pipeline on the
    OCR path, untouched on the parser path — a parser says what the file
    contains, not what state the document should be left in, which is the
    caller's decision (approving it, or handing it back for review).
    """

    document: Document
    #: The periods the file turned out to cover. Only a parser knows them; an
    #: OCR'd document's figures reach a report through its type's concept
    #: mapping instead.
    periods: tuple[str, ...] = ()
    #: The machine-readable source it was recognised as, when a parser claimed
    #: it. `None` means it went through classification and OCR.
    source_id: str | None = None


class ExtractDocument:
    """Reads a document's file and persists what it says.

    Two paths, chosen by the file rather than by the person:

    * A format with a dedicated parser (a tax authority's generated
      spreadsheet) is read exactly, with no AI in the path. Nobody is asked to
      pick it: the parsers say whether they recognise the bytes, which is a
      better answer than a menu.
    * Anything else goes through classification and OCR against the configured
      document types, exactly as an arriving upload would.

    Shared by the two acts that read a file after it has already landed —
    approving it and reprocessing it — so neither can drift into reading a
    spreadsheet with an AI while the other reads it with its parser.
    """

    def __init__(
        self,
        storage: DocumentStorage,
        parsers: DocumentSourceParsers,
        extracted_data: ExtractedDataRepository,
        process_document: ProcessUploadedDocument,
    ) -> None:
        self._storage = storage
        self._parsers = parsers
        self._extracted_data = extracted_data
        self._process_document = process_document

    def execute(self, document: Document) -> DocumentExtraction:
        parsed = self._parse(document)
        if parsed is not None:
            self._save_extraction(document.id, parsed.summary)
            return DocumentExtraction(
                document=document,
                periods=parsed.periods,
                source_id=parsed.source_id,
            )

        # No parser claims this file, so it is a document like any other:
        # classified against the configured types and OCR'd with the winner's
        # prompt. Re-run rather than trusted, because both callers are asking
        # precisely because an earlier run produced nothing usable — or because
        # the type has been configured since.
        extracted = self._process_document.execute(
            ProcessUploadedDocumentInput(
                client_id=document.client_id,
                drive_file_id=document.drive_file_id,
                file_reference=document.drive_file_id,
                # Without this a second run would leave a second document
                # behind for the same file.
                replace_existing=True,
            )
        )
        return DocumentExtraction(document=extracted)

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
