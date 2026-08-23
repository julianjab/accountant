import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from server.domain.entities import Document, DocumentStatus, ExtractedData
from server.domain.ports import (
    DocumentClassifier,
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
