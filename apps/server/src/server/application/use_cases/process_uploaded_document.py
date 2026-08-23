import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from server.domain.entities import Document, DocumentStatus, ExtractedData
from server.domain.ports import (
    DocumentClassifier,
    DocumentContent,
    DocumentRepository,
    DocumentStorage,
    DocumentTypeRepository,
    ExtractedDataRepository,
    OcrEngine,
)


@dataclass(frozen=True, slots=True)
class ProcessUploadedDocumentInput:
    client_id: str
    drive_file_id: str
    file_reference: str


class ProcessUploadedDocument:
    """Triggered when a new document arrives (Drive webhook):
    1) classifies the document type against the configured types,
    2) runs that type's OCR extraction,
    3) persists the extracted data."""

    def __init__(
        self,
        storage: DocumentStorage,
        classifier: DocumentClassifier,
        ocr: OcrEngine,
        documents: DocumentRepository,
        document_types: DocumentTypeRepository,
        extracted_data: ExtractedDataRepository,
    ) -> None:
        self._storage = storage
        self._classifier = classifier
        self._ocr = ocr
        self._documents = documents
        self._document_types = document_types
        self._extracted_data = extracted_data

    def execute(self, data: ProcessUploadedDocumentInput) -> Document:
        # Nothing is persisted until this succeeds, so a caller (the Drive
        # webhook's at-least-once retry) can safely treat a raised exception
        # here as "nothing happened yet, try again".
        content = self._storage.download(data.file_reference)

        document = Document(
            id=str(uuid.uuid4()),
            client_id=data.client_id,
            document_type_id=None,
            drive_file_id=data.drive_file_id,
            file_name=content.file_name,
            mime_type=content.mime_type,
            status=DocumentStatus.CLASSIFYING,
            error=None,
            created_at=datetime.now(UTC),
        )
        self._documents.save(document)

        # From here on, every step writes to `document`'s row. Letting an
        # exception (a classifier/OCR timeout, a transient Firestore error, a
        # 5xx from Anthropic, ...) escape past this point would leave that row
        # stuck in CLASSIFYING/RUNNING_OCR forever with no visible error and no
        # safe way for a caller to retry without risking a duplicate document
        # for the same file. Converting it to a FAILED document instead keeps
        # `execute` always returning a terminal, inspectable result.
        try:
            return self._classify_and_extract(document, content)
        except Exception as exc:
            # If this save also fails (the repository itself is down), the
            # exception propagates and the row above stays CLASSIFYING/
            # RUNNING_OCR; a caller would then, incorrectly, treat that as
            # "nothing persisted, safe to retry" and create another row. That
            # residual case needs the repository itself to be healthy to
            # resolve, which is outside what this use case can guarantee.
            document = _with_error(document, str(exc))
            self._documents.save(document)
            return document

    def _classify_and_extract(self, document: Document, content: DocumentContent) -> Document:
        available_types = self._document_types.list_active()
        document_type = self._classifier.classify(content, available_types)
        if document_type is None:
            document = _with_error(document, "Could not identify the document type")
            self._documents.save(document)
            return document

        document = _with_status(document, DocumentStatus.RUNNING_OCR, document_type.id)
        self._documents.save(document)

        fields = self._ocr.extract(content, document_type)
        self._extracted_data.save(
            ExtractedData(
                id=str(uuid.uuid4()),
                document_id=document.id,
                fields=fields,
                confidence=None,
                created_at=datetime.now(UTC),
            )
        )

        document = _with_status(document, DocumentStatus.PROCESSED, document_type.id)
        self._documents.save(document)
        return document


def _with_status(document: Document, status: DocumentStatus, document_type_id: str) -> Document:
    return Document(
        id=document.id,
        client_id=document.client_id,
        document_type_id=document_type_id,
        drive_file_id=document.drive_file_id,
        file_name=document.file_name,
        mime_type=document.mime_type,
        status=status,
        error=None,
        created_at=document.created_at,
        processed_at=datetime.now(UTC)
        if status == DocumentStatus.PROCESSED
        else document.processed_at,
    )


def _with_error(document: Document, error: str) -> Document:
    return Document(
        id=document.id,
        client_id=document.client_id,
        document_type_id=document.document_type_id,
        drive_file_id=document.drive_file_id,
        file_name=document.file_name,
        mime_type=document.mime_type,
        status=DocumentStatus.FAILED,
        error=error,
        created_at=document.created_at,
        processed_at=document.processed_at,
    )
