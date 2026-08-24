from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DocumentStatus(StrEnum):
    PENDING = "pending"
    CLASSIFYING = "classifying"
    RUNNING_OCR = "running_ocr"
    PROCESSED = "processed"
    APPROVED = "approved"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    client_id: str
    document_type_id: str | None
    drive_file_id: str
    file_name: str
    mime_type: str
    status: DocumentStatus
    error: str | None
    created_at: datetime
    processed_at: datetime | None = None
    reviewed_at: datetime | None = None
    approved_by: str | None = None
    #: The machine-readable source this file was recognised as, when it is one.
    #: Some documents are read by a dedicated parser rather than by OCR against
    #: a configured document type — a tax authority's generated spreadsheet, for
    #: instance — so they never get a `document_type_id` and would otherwise
    #: stay indistinguishable from a document nothing could be made of.
    source_id: str | None = None
