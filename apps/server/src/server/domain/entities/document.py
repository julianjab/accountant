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
